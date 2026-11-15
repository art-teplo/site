from django.core.management.base import BaseCommand, CommandError

from ...importers.velar import import_velar
from ...importers.xlsx import PriceFileError

HELP = (
    'Импорт прайса Velar (xlsx завода, профильные радиаторы): серии, '
    'варианты по подключениям и цены в RUB. Новые серии — неопубликованные '
    '(--publish — сразу на сайте). Повторный импорт обновляет варианты и '
    'цены, пропавшие скрывает; у серии заполняет только пустые поля.'
)
TOTAL = (
    'Серий {series} (новых {new}); вариантов новых {created}, '
    'обновлено {updated}, скрыто {hidden}'
)
SERIES = '  {name} ({slug}){new}: вариантов {variants}{groups}'
NEW = ', новая'
GROUPS = '; группы цветов: {}'
SKIPPED = '  пропущены листы: {}'
ERROR = '  внимание: {}'
DRY_RUN = 'Пробный прогон: ничего не сохранено'


class Command(BaseCommand):
    help = HELP

    def add_arguments(self, parser):
        parser.add_argument('path', help='путь к xlsx')
        parser.add_argument(
            '--publish',
            action='store_true',
            help='новые серии сразу на сайте',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='посчитать и откатить',
        )

    def handle(self, *args, path, publish, dry_run, **options):  # noqa: ARG002
        try:
            summary = import_velar(path, publish=publish, dry_run=dry_run)
        except PriceFileError as error:
            raise CommandError(str(error)) from error
        for result in summary.series:
            self.stdout.write(
                SERIES.format(
                    name=result.series.name,
                    slug=result.series.slug,
                    new=NEW if result.created else '',
                    variants=result.variants,
                    groups=(
                        GROUPS.format(', '.join(result.groups))
                        if result.groups
                        else ''
                    ),
                ),
            )
        if summary.skipped:
            self.stdout.write(SKIPPED.format(', '.join(summary.skipped)))
        for error in summary.errors:
            self.stdout.write(self.style.WARNING(ERROR.format(error)))
        self.stdout.write(
            self.style.SUCCESS(
                TOTAL.format(
                    series=len(summary.series),
                    new=sum(r.created for r in summary.series),
                    created=summary.created,
                    updated=summary.updated,
                    hidden=summary.hidden,
                ),
            ),
        )
        if dry_run:
            self.stdout.write(DRY_RUN)
