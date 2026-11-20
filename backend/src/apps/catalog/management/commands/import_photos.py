from django.core.management.base import BaseCommand

from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend

from ...importers.factory_editions import legacy_targets
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
        splits = legacy_targets()
        possible = [
            target
            for slug in slugs
            for target in (slug, *splits.get(slug, ()))
        ]
        found = {s.slug: s for s in Series.objects.filter(slug__in=possible)}
        destinations = [
            target
            for slug in slugs
            for target in (
                [child for child in splits.get(slug, ()) if child in found]
                or [slug]
            )
        ]
        with muted_revalidation():
            for slug in destinations:
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
