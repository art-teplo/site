import hashlib
import io
import json
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image

from apps.catalog.importers.kzto import absolute, fetch
from apps.catalog.importers.kzto_media import sync_kzto_media
from apps.catalog.importers.kzto_page import Document, Page
from apps.catalog.models import Series, Showcase
from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend

DEFAULT_SOURCE = (
    Path(__file__).resolve().parents[2] / 'data/kzto_media_sources.json'
)


class Command(BaseCommand):
    help = 'Дополнить собственные фото и документы серий КЗТО; без --apply только отчёт.'

    def add_arguments(self, parser):
        parser.add_argument('--inventory', default=str(DEFAULT_SOURCE))
        parser.add_argument('--series', action='append')
        parser.add_argument('--cache-dir')
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--report')

    def save_card(self, series, url, download):
        data = download(absolute(url))
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            image.verify()
        orientation = list(
            series.variants.order_by()
            .values_list('orientation', flat=True)
            .distinct()
        )
        label = (
            'Вертикальный'
            if orientation == ['v']
            else 'Горизонтальный'
            if orientation == ['h']
            else series.name
        )
        card = Showcase(series=series, label=label, image_alt=series.name)
        card.image.save(f'{series.slug}.webp', ContentFile(data), save=False)
        card.image_width, card.image_height = width, height
        card.save()

    def enrich_series(self, series, row, download, report):
        if not series.description.strip() and row.get('description'):
            series.description = row['description']
            series.save(update_fields=['description'])
            report['description_filled'] = True
        if row.get('tile_url') and not series.showcases.exists():
            try:
                self.save_card(series, row['tile_url'], download)
                report['card_created'] = True
            except (OSError, ValueError) as error:
                report['errors'].append(f'Превью: {error}')

    def handle(self, *args, **options):  # noqa: ARG002
        rows = json.loads(Path(options['inventory']).read_text())['rows']
        rows = [
            r
            for r in rows
            if not options['series'] or r['series_slug'] in options['series']
        ]
        owners = {
            s.slug: s
            for s in Series.objects.filter(
                brand__slug='kzto', slug__in=[r['series_slug'] for r in rows]
            )
        }
        missing = sorted({r['series_slug'] for r in rows} - owners.keys())
        if missing:
            message = f'Сначала разделите серии: {missing}'
            raise CommandError(message)

        def download(url):
            if options['cache_dir']:
                cached = (
                    Path(options['cache_dir'])
                    / hashlib.sha256(url.encode()).hexdigest()
                )
                if cached.exists():
                    return cached.read_bytes()
            return fetch(url)

        reports = {}
        with muted_revalidation():
            for row in rows:
                series = owners[row['series_slug']]
                page = Page(
                    gallery=row['gallery'],
                    documents=[Document(**d) for d in row['documents']],
                )
                report = sync_kzto_media(
                    series,
                    page,
                    dry_run=not options['apply'],
                    fetcher=download,
                    photo_kinds=row.get('photo_kinds'),
                )
                if options['apply']:
                    self.enrich_series(series, row, download, report)
                reports[series.slug] = report
                self.stdout.write(
                    f'{series.slug}: {json.dumps(report, ensure_ascii=False)}'
                )
        if options['apply'] and any(
            r['images']
            or r['files']
            or r.get('card_created')
            or r.get('description_filled')
            for r in reports.values()
        ):
            transaction.on_commit(
                lambda: revalidate_frontend.delay(Tag.CATALOG)
            )
        if options['report']:
            Path(options['report']).write_text(
                json.dumps(reports, ensure_ascii=False, indent=2)
            )
