import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import ConnectionOption, Series
from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend

DEFAULT_SOURCE = (
    Path(__file__).resolve().parents[2] / 'data/kzto_connections.json'
)


class Command(BaseCommand):
    help = 'Проверенные подключения КЗТО и фиксированные доплаты. Без --apply только отчёт.'

    def add_arguments(self, parser):
        parser.add_argument('--source', default=str(DEFAULT_SOURCE))
        parser.add_argument('--series', action='append')
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):  # noqa: ARG002
        source = json.loads(Path(options['source']).read_text())
        rows = [
            r
            for r in source['rules']
            if not options['series'] or r['series_slug'] in options['series']
        ]
        series = {
            s.slug: s
            for s in Series.objects.filter(
                brand__slug='kzto', slug__in={r['series_slug'] for r in rows}
            )
        }
        missing = sorted({r['series_slug'] for r in rows} - series.keys())
        if missing:
            message = f'Сначала разделите серии: {missing}'
            raise CommandError(message)
        changed = False
        with muted_revalidation(), transaction.atomic():
            for row in rows:
                data = row.copy()
                owner = series[data.pop('series_slug')]
                source_id, tubes, mount = (
                    data.pop('source_id'),
                    data.pop('tubes'),
                    data.pop('mount'),
                )
                option, created = ConnectionOption.objects.get_or_create(
                    series=owner,
                    source_id=source_id,
                    tubes=tubes,
                    mount=mount,
                    defaults=data,
                )
                changed = changed or created
                # Повторный импорт не затирает исправленные менеджером суммы.
                if (
                    not created
                    and option.checked_on.isoformat() < data['checked_on']
                ):
                    for key, value in data.items():
                        setattr(option, key, value)
                    option.full_clean()
                    option.save()
                    changed = True
            for owner in series.values():
                if (
                    owner.variants.filter(is_active=True).exists()
                    and owner.configured_coverage()
                    and owner.offer_mode != 'configured'
                ):
                    owner.offer_mode = 'configured'
                    owner.full_clean()
                    owner.save(update_fields=['offer_mode'])
                    changed = True
            if not options['apply']:
                transaction.set_rollback(True)
            elif changed:
                transaction.on_commit(
                    lambda: revalidate_frontend.delay(Tag.CATALOG)
                )
        self.stdout.write(
            json.dumps(
                {
                    'rules': len(rows),
                    'series': len(series),
                    'applied': options['apply'],
                },
                ensure_ascii=False,
            )
        )
