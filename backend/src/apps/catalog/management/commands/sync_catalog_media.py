import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.importers.catalog_media import download, sync_catalog_media

DEFAULT_SOURCE = (
    Path(__file__).resolve().parents[2] / 'data/factory_media_sources.json'
)


class Command(BaseCommand):
    help = 'Дополнить отобранные фото и документы каталога. Без --apply — только отчёт.'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
        parser.add_argument('--report', type=Path, required=True)
        parser.add_argument('--series', action='append')
        parser.add_argument('--cache-dir', type=Path)
        parser.add_argument('--local-dir', type=Path)
        parser.add_argument('--local-media', action='store_true')
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):  # noqa: ARG002
        if options['local_media'] and not settings.DEBUG:
            msg = '--local-media доступен только при DEBUG'
            raise CommandError(msg)
        rows = json.loads(options['source'].read_text())['rows']
        if options['series']:
            rows = [r for r in rows if r['series'] in options['series']]

        def fetcher(url):
            parsed = urlsplit(url)
            if parsed.scheme == 'file':
                filename = unquote(parsed.path).removeprefix('/')
                root = options['local_dir']
                if (
                    root is None
                    or parsed.netloc
                    or '/' in filename
                    or not filename
                ):
                    msg = 'Укажите --local-dir для локального оригинала'
                    raise ValueError(msg)
                return (root / filename).read_bytes()

            cached = (
                options['cache_dir'] / hashlib.sha256(url.encode()).hexdigest()
                if options['cache_dir']
                else None
            )
            if cached and cached.exists():
                return cached.read_bytes()
            data = download(url)
            if cached:
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_bytes(data)
            return data

        result = sync_catalog_media(
            rows,
            apply=options['apply'],
            fetcher=fetcher,
            local_media=options['local_media'],
        )
        options['report'].write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        )
        self.stdout.write(json.dumps(result, ensure_ascii=False))
