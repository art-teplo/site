"""Адресная привязка линеек и проверка происхождения признаков."""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.importers.product_families import (
    assign_family,
    family_for_target,
)
from apps.catalog.importers.velar import (
    FLOOR_SHEET,
    SHEETS,
    Summary,
    parse_sheet,
)
from apps.catalog.importers.xlsx import _open
from apps.catalog.models import Series, Variant
from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend


class Command(BaseCommand):
    help = 'Линейки и признаки из подтверждённых источников. Без --apply только отчёт.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--report')
        parser.add_argument('--velar-source')

    def handle(self, *args, **options):  # noqa: ARG002
        if options['apply'] and not options['report']:
            message = 'Для применения нужен --report с исходными значениями'
            raise CommandError(message)
        changes = []
        with muted_revalidation(), transaction.atomic():
            for series in Series.objects.filter(
                category__slug='radiatory'
            ).select_related('brand', 'category'):
                if not family_for_target(series.brand.slug, series.slug):
                    continue
                before = {
                    k: getattr(series, k)
                    for k in ('family_id', 'factory_orientation', 'offer_mode')
                }
                assign_family(series)
                if (
                    series.brand.slug == 'kzto'
                    and series.connection_options.exists()
                    and series.configured_coverage()
                ):
                    series.offer_mode = 'configured'
                    series.full_clean()
                    series.save(update_fields=['offer_mode'])
                after = {k: getattr(series, k) for k in before}
                if before != after:
                    changes.append(
                        {
                            'model': 'series',
                            'pk': series.pk,
                            'before': before,
                            'after': after,
                        }
                    )
            if options['velar_source']:
                changes.extend(self.audit_velar(options['velar_source']))
            report = {'applied': options['apply'], 'changes': changes}
            if options['report']:
                Path(options['report']).write_text(
                    json.dumps(report, ensure_ascii=False, indent=2) + '\n'
                )
            if not options['apply']:
                transaction.set_rollback(True)
            elif changes:
                transaction.on_commit(
                    lambda: revalidate_frontend.delay(Tag.CATALOG)
                )
        self.stdout.write(
            json.dumps(
                {'applied': options['apply'], 'changes': len(changes)},
                ensure_ascii=False,
            )
        )

    def audit_velar(self, source):
        book = _open(source)
        variants = {
            (v.article, v.connection): v
            for v in Variant.objects.filter(
                brand__slug='velar'
            ).select_related('series')
        }
        changes = []
        try:
            for title in book.sheetnames:
                if title not in SHEETS and title != FLOOR_SHEET:
                    continue
                rows, _ = parse_sheet(
                    title, book[title].iter_rows(values_only=True), Summary()
                )
                for row in rows:
                    variant = variants.get((row.article, row.connection))
                    if (
                        variant is None
                        or variant.series.slug != row.sheet.slug
                    ):
                        continue
                    if any(
                        getattr(variant, k) != row.values.get(k)
                        for k in ('height_mm', 'width_mm', 'depth_mm')
                    ):
                        continue  # не перезаписывать неподтверждённую/ручную геометрию
                    confirmed = variant.attrs.get('confirmed_fields', [])
                    before = {
                        'mount': variant.mount,
                        'thermovalve': variant.thermovalve,
                    }
                    if (
                        'mount' not in confirmed
                        and variant.mount == 'wall'
                        and not row.sheet.mount
                    ):
                        variant.mount = ''
                    if (
                        'thermovalve' not in confirmed
                        and variant.thermovalve is False
                    ):
                        variant.thermovalve = None
                    after = {
                        'mount': variant.mount,
                        'thermovalve': variant.thermovalve,
                    }
                    if before != after:
                        changes.append(
                            {
                                'model': 'variant',
                                'pk': variant.pk,
                                'article': variant.article,
                                'before': before,
                                'after': after,
                            }
                        )
                        variant.save(update_fields=list(after))
        finally:
            book.close()
        return changes
