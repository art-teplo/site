import json
from pathlib import Path

from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q

from apps.catalog.archive_transfer import targets, transfer_archive
from apps.catalog.models import (
    ColorGroup,
    ProductFamily,
    Series,
    SeriesFile,
    SeriesImage,
)
from apps.content.models import Project, Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend


class Command(BaseCommand):
    help = 'Перенести материалы и удалить архивных родителей. Без --apply проверка откатывается.'

    def add_arguments(self, parser):
        parser.add_argument('--report', type=Path, required=True)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):  # noqa: ARG002
        registry = targets()
        slugs = set(registry) | {
            s for children in registry.values() for s in children
        }
        with muted_revalidation(), transaction.atomic():
            related = list(
                Series.objects.select_for_update()
                .filter(slug__in=slugs)
                .order_by('pk')
            )
            parents = [
                s for s in related if s.slug in registry and not s.is_published
            ]
            ids = [s.pk for s in related]
            backup = []
            for queryset in (
                Series.objects.filter(pk__in=ids),
                ColorGroup.objects.filter(series_id__in=ids),
                SeriesImage.objects.filter(series_id__in=ids),
                SeriesFile.objects.filter(series_id__in=ids),
                ProductFamily.objects.filter(
                    Q(pk__in=[s.family_id for s in related if s.family_id])
                    | Q(presentation_photo__series_id__in=ids)
                ),
                Project.series.through.objects.filter(series_id__in=ids),
            ):
                backup.extend(
                    serializers.serialize('python', queryset.order_by('pk'))
                )
            try:
                results = [transfer_archive(parent) for parent in parents]
                with options['report'].open('x', encoding='utf-8') as report:
                    json.dump(
                        {
                            'applied': options['apply'],
                            'transferred': results,
                            'backup': backup,
                        },
                        report,
                        ensure_ascii=False,
                        indent=2,
                        cls=DjangoJSONEncoder,
                    )
                    report.write('\n')
            except (ValueError, OSError) as error:
                raise CommandError(str(error)) from error
            if not options['apply']:
                transaction.set_rollback(True)
            elif results:
                transaction.on_commit(
                    lambda: revalidate_frontend.delay(Tag.CATALOG)
                )
        self.stdout.write(
            f'Серий: {len(results)}, применение: {options["apply"]}'
        )
