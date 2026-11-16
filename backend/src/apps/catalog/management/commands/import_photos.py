from django.core.management.base import BaseCommand

from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend

from ...importers.factory_photos import Summary, import_series, slugs_for
from ...models import Series


class Command(BaseCommand):
    help = (
        'Витринные фото с сайтов заводов (guardo.ru — рендеры по высотам, '
        'kztoradiator.ru — плитки Ellipse и Quadrum, velarwh.ru — превью и '
        'интерьерные рендеры) первыми в галерею серии. '
        'Повторный запуск не дублирует'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--brand',
            choices=['guardo', 'kzto', 'velar', 'all'],
            default='all',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Скачать и показать, ничего не сохраняя',
        )

    def handle(self, *_args, brand, dry_run, **_options):
        summary = Summary()
        slugs = slugs_for(brand)
        found = {s.slug: s for s in Series.objects.filter(slug__in=slugs)}
        with muted_revalidation():
            for slug in slugs:
                series = found.get(slug)
                if series is None:
                    self.stdout.write(f'{slug}: серии нет — пропуск')
                    continue
                before = len(summary.lines)
                import_series(series, summary, dry_run=dry_run)
                for line in summary.lines[before:]:
                    self.stdout.write(f'  {line}')
        if summary.added and not dry_run:
            revalidate_frontend.delay(Tag.CATALOG)
        for error in summary.errors:
            self.stderr.write(error)
        verb = 'Будет добавлено' if dry_run else 'Добавлено'
        self.stdout.write(
            self.style.SUCCESS(
                f'{verb} фото: {summary.added}, уже были: {summary.skipped}',
            ),
        )
