import time

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.importers.xlsx import PriceFileError, import_file

HELP = (
    'Импорт прайса Guardo и Nova из xlsx-выгрузки: серии, варианты, цены. '
    'Новые серии — неопубликованные, их публикует менеджер. Группы цветов '
    'создаёт только первый импорт серии. Повторный импорт обновляет числа '
    'и цены, пропавшие варианты скрывает; описание, фото и группы цветов не '
    'трогает, а цвета вне групп перечисляет.'
)
KEPT_PRICE = (
    'цена оставлена прежней у {count} вариантов: ни одного их цвета нет '
    'в группах серии — проверьте группы'
)
DRY_RUN = 'Пробный прогон: ничего не сохранено'
SHEET_LINE = (
    '{sheet}: строк {rows}; серий новых {new} из {total}; вариантов '
    'новых {created}, обновлено {updated}, скрыто {hidden}'
)
NEW_SERIES = '  новая серия: {name} ({slug}, {category})'
SERIES = '  серия: {name} ({slug})'
GROUP = '    группа «{name}»: {percent}, артикулов {count}{note}'
CHEAPER = ' ⚠ дешевле базового'
SKIPPED_COLOR = (
    '    пропущены, проверьте прайс: {color} {percent}, артикулов {count}'
)
UNGROUPED = '  {slug}: новые цвета, не в группах: {colors}'
SKIPPED_ROWS = '  пропущено строк: {count} — {models}'
DUPLICATES = (
    '  повторы артикула, подключения и цвета (оставлена одна строка): {count}'
)
TWINS = '  артикулов с повёрнутым двойником (два варианта): {count}'
CONFLICTS = (
    '  один артикул и подключение с разными размерами или в двух сериях — '
    'оставлена одна строка: {count} артикулов, например {examples}'
)
ERROR = '  не импортировано: {}'
DONE = 'Готово за {seconds:.0f} с'
ANY_RAL_PERCENT = 'по запросу'
UNKNOWN_PERCENT = 'надбавка неизвестна'


def percent_label(percent) -> str:
    if percent is None:
        return UNKNOWN_PERCENT
    if percent < 0:
        return f'−{abs(percent):g} %'
    return f'+{percent:g} %' if percent else '0 %'


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
        except PriceFileError as error:
            raise CommandError(str(error)) from error
        for summary in summaries:
            self.write_summary(summary)
        if options['dry_run']:
            self.stdout.write(self.style.WARNING(DRY_RUN))
        seconds = time.monotonic() - started
        self.stdout.write(self.style.SUCCESS(DONE.format(seconds=seconds)))

    def write_summary(self, summary):
        self.stdout.write(
            SHEET_LINE.format(
                sheet=summary.sheet,
                rows=summary.rows,
                new=len(summary.series_new),
                total=len(summary.series),
                created=summary.created,
                updated=summary.updated,
                hidden=summary.hidden,
            ),
        )
        for report in summary.series:
            self.write_series(report)
        if summary.skipped:
            models = ', '.join(
                f'{model} {count}'
                for model, count in summary.skipped.most_common()
            )
            self.stdout.write(
                SKIPPED_ROWS.format(
                    count=summary.skipped.total(),
                    models=models,
                ),
            )
        if summary.duplicates:
            self.stdout.write(DUPLICATES.format(count=summary.duplicates))
        if summary.twins:
            self.stdout.write(TWINS.format(count=summary.twins))
        if summary.kept_price:
            self.stdout.write(KEPT_PRICE.format(count=summary.kept_price))
        if summary.conflicts:
            self.stdout.write(
                CONFLICTS.format(
                    count=len(summary.conflicts),
                    examples=', '.join(list(summary.conflicts)[:3]),
                ),
            )
        for error in summary.errors:
            self.stdout.write(self.style.ERROR(ERROR.format(error)))

    def write_series(self, report):
        series = report.series
        if report.created:
            self.stdout.write(
                NEW_SERIES.format(
                    name=series.name,
                    slug=series.slug,
                    category=series.category.slug,
                ),
            )
        elif report.groups or report.skipped:
            self.stdout.write(
                SERIES.format(name=series.name, slug=series.slug)
            )
        for name, percent, count in report.groups:
            label = ANY_RAL_PERCENT if percent is None else None
            self.stdout.write(
                GROUP.format(
                    name=name,
                    percent=label or percent_label(percent),
                    count=count,
                    note=CHEAPER
                    if percent is not None and percent < 0
                    else '',
                ),
            )
        for color, percent, count in report.skipped:
            self.stdout.write(
                self.style.WARNING(
                    SKIPPED_COLOR.format(
                        color=color,
                        percent=percent_label(percent),
                        count=count,
                    ),
                ),
            )
        if report.ungrouped:
            self.stdout.write(
                self.style.WARNING(
                    UNGROUPED.format(
                        slug=series.slug,
                        colors=', '.join(report.ungrouped),
                    ),
                ),
            )
