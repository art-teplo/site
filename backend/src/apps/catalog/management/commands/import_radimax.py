from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.importers.radimax import (
    PRICE_SOURCE,
    build_variants,
    import_radimax,
    read_price,
)


class Command(BaseCommand):
    help = 'Импортировать розничные цены Радимакс в BYN. Без --apply — только отчёт.'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=Path, default=PRICE_SOURCE)
        parser.add_argument('--series', action='append')
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):  # noqa: ARG002
        try:
            variants = [
                row
                for row in build_variants(read_price(options['source']))
                if not options['series']
                or row['series'] in options['series']
                or row['former_series'] in options['series']
            ]
        except (KeyError, OSError, ValueError) as error:
            raise CommandError(str(error)) from error
        if not variants:
            msg = 'Нет вариантов для выбранных серий'
            raise CommandError(msg)
        if len({row['article'] for row in variants}) != len(variants):
            msg = 'В прайсе есть повторяющиеся артикулы'
            raise CommandError(msg)
        summary = f'Серий: {len({row["series"] for row in variants})}, вариантов: {len(variants)}'
        self.stdout.write(summary)
        if options['apply']:
            try:
                self.stdout.write(str(import_radimax(variants)))
            except ValueError as error:
                raise CommandError(str(error)) from error
