import time

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.importers.xlsx import PriceFileError, import_file

HELP = (
    'Импорт прайса Guardo и Nova из xlsx-выгрузки: серии, варианты, цены. '
    'Новые серии — неопубликованные, их публикует менеджер. Повторный '
    'импорт обновляет числа и цены, пропавшие варианты скрывает; описание, '
    'фото, группы цветов и проценты не трогает.'
)
DRY_RUN = 'Пробный прогон: ничего не сохранено'
SHEET_LINE = (
    '{sheet}: строк {rows}; серий новых {new} из {total}; вариантов '
    'новых {created}, обновлено {updated}, скрыто {hidden}'
)
NEW_SERIES = '  новая серия: {name} ({slug}, {category})'
SKIPPED = '  пропущено строк: {count} — {models}'
DUPLICATES = '  повторы артикула и цвета (взята первая строка): {count}'
CONFLICTS = (
    '  один артикул с разными размерами или подключением — взята одна '
    'строка: {count} артикулов, например {examples}'
)
DONE = 'Готово за {seconds:.0f} с'


class Command(BaseCommand):
    help = HELP

    def add_arguments(self, parser):
        parser.add_argument('path', help='xlsx-выгрузка')
        parser.add_argument(
            '--sheet',
            action='append',
            dest='sheets',
            help='лист, можно несколько раз; по умолчанию Guardo и Nova',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='посчитать и откатить',
        )

    def handle(self, *args, **options):  # noqa: ARG002
        started = time.monotonic()
        try:
            summaries = import_file(
                options['path'],
                options['sheets'],
                dry_run=options['dry_run'],
            )
        except (PriceFileError, FileNotFoundError) as error:
            raise CommandError(str(error)) from error
        for summary in summaries:
            self.stdout.write(
                SHEET_LINE.format(
                    sheet=summary.sheet,
                    rows=summary.rows,
                    new=len(summary.series_new),
                    total=summary.series_total,
                    created=summary.created,
                    updated=summary.updated,
                    hidden=summary.hidden,
                ),
            )
            for series in summary.series_new:
                self.stdout.write(
                    NEW_SERIES.format(
                        name=series.name,
                        slug=series.slug,
                        category=series.category.slug,
                    ),
                )
            if summary.skipped:
                models = ', '.join(
                    f'{model} {count}'
                    for model, count in summary.skipped.most_common()
                )
                self.stdout.write(
                    SKIPPED.format(
                        count=summary.skipped.total(),
                        models=models,
                    ),
                )
            if summary.duplicates:
                self.stdout.write(DUPLICATES.format(count=summary.duplicates))
            if summary.conflicts:
                examples = ', '.join(list(summary.conflicts)[:3])
                self.stdout.write(
                    CONFLICTS.format(
                        count=len(summary.conflicts),
                        examples=examples,
                    ),
                )
        if options['dry_run']:
            self.stdout.write(self.style.WARNING(DRY_RUN))
        seconds = time.monotonic() - started
        self.stdout.write(self.style.SUCCESS(DONE.format(seconds=seconds)))
