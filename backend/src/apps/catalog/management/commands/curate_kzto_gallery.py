import json

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.catalog.gallery_curation import gallery_rules
from apps.catalog.models import SeriesImage
from apps.content.models import Tag
from apps.content.tasks import revalidate_frontend


class Command(BaseCommand):
    help = 'Скрыть отобранные повторы только в галереях КЗТО; файлы не удаляются. Без --apply только отчёт.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):  # noqa: ARG002
        report = {}
        with transaction.atomic():
            for slug, rule in gallery_rules().items():
                images = SeriesImage.objects.filter(
                    series__slug=slug,
                    series__brand__slug='kzto',
                    is_visible=True,
                ).filter(
                    Q(source_url__in=rule['hidden_source_urls'])
                    | Q(image__in=rule['hidden_image_files'])
                )
                report[slug] = images.count()
                if options['apply']:
                    images.update(is_visible=False)
            if options['apply'] and any(report.values()):
                transaction.on_commit(
                    lambda: revalidate_frontend.delay(Tag.CATALOG)
                )
        self.stdout.write(
            json.dumps(
                {'hidden': report, 'applied': options['apply']},
                ensure_ascii=False,
            )
        )
