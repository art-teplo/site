import time

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.importers.kzto import FEED_URL, FeedError, import_kzto

HELP = (
    'Импорт КЗТО с kztoradiator.ru: серии, варианты и цены в RUB — из '
    'YML-фида; описание, параметры, фото и PDF — со страниц серий. Новые '
    'серии — неопубликованные (--publish — сразу на сайте). Повторный '
    'импорт обновляет варианты и цены, пропавшие скрывает; у серии '
    'заполняет только пустые поля, фото и PDF — если их ещё нет.'
)
TOTAL = (
    'Предложений в фиде {offers}; серий {series} (новых {new}); вариантов '
    'новых {created}, обновлено {updated}, скрыто {hidden}'
)
SERIES = '  {name} ({slug}){new}: вариантов {offers}{filled}{media}'
NEW = ', новая'
FILLED = '; заполнено: {}'
MEDIA = '; фото {images}, PDF {files}'
SKIPPED = '  не берём: {}'
UNKNOWN = '  новые категории фида, не импортированы — добавьте в TARGETS: {}'
RENAMED = (
    '  повтор артикула в фиде, второй вариант записан по названию: {count}, '
    'например {examples}'
)
ERROR = '  ошибка: {}'
DRY_RUN = 'Пробный прогон: ничего не сохранено'
DONE = 'Готово за {seconds:.0f} с'


def _counts(counter) -> str:
    return ', '.join(f'{name} ({count})' for name, count in counter.items())


class Command(BaseCommand):
    help = HELP

    def add_arguments(self, parser):
        parser.add_argument(
            '--feed',
            default=FEED_URL,
            help='адрес или путь к YML-фиду, по умолчанию — фид завода',
        )
        parser.add_argument(
            '--no-pages',
            action='store_true',
            help='без страниц серий: только фид (без описаний и PDF)',
        )
        parser.add_argument(
            '--no-media',
            action='store_true',
            help='не скачивать фото и PDF',
        )
        parser.add_argument(
            '--publish',
            action='store_true',
            help='новые серии сразу на сайте',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='посчитать и откатить, без фото и PDF',
        )

    def handle(self, *args, **options):  # noqa: ARG002
        started = time.monotonic()
        try:
            summary = import_kzto(
                options['feed'],
                pages=not options['no_pages'],
                media=not options['no_media'],
                publish=options['publish'],
                dry_run=options['dry_run'],
            )
        except FeedError as error:
            raise CommandError(str(error)) from error
        self.write_summary(summary)
        if options['dry_run']:
            self.stdout.write(self.style.WARNING(DRY_RUN))
        seconds = time.monotonic() - started
        self.stdout.write(self.style.SUCCESS(DONE.format(seconds=seconds)))

    def write_summary(self, summary):
        out = self.stdout
        out.write(
            TOTAL.format(
                offers=summary.offers,
                series=len(summary.series),
                new=sum(1 for r in summary.series if r.created),
                created=summary.created,
                updated=summary.updated,
                hidden=summary.hidden,
            ),
        )
        for result in summary.series:
            has_media = result.images or result.files
            out.write(
                SERIES.format(
                    name=result.series.name,
                    slug=result.series.slug,
                    new=NEW if result.created else '',
                    offers=result.offers,
                    filled=(
                        FILLED.format(', '.join(result.filled))
                        if result.filled
                        else ''
                    ),
                    media=(
                        MEDIA.format(images=result.images, files=result.files)
                        if has_media
                        else ''
                    ),
                ),
            )
        if summary.skipped:
            out.write(SKIPPED.format(_counts(summary.skipped)))
        if summary.unknown:
            out.write(
                self.style.WARNING(UNKNOWN.format(_counts(summary.unknown)))
            )
        if summary.renamed:
            examples = ', '.join(name for _, name in summary.renamed[:3])
            out.write(
                RENAMED.format(count=len(summary.renamed), examples=examples),
            )
        for error in summary.errors:
            out.write(self.style.ERROR(ERROR.format(error)))
