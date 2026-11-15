"""PDF заводов к сериям (решение № 166): каталоги и паспорта guardo.ru.

Один PDF на несколько серий (каталог Retta — у всех четырёх Retta)
загружается в хранилище один раз, остальные записи ссылаются на тот же
файл: файлы серий при удалении записи не стираются. Повторный запуск не
дублирует: файл с тем же названием у серии уже есть — пропуск.
"""

from dataclasses import dataclass, field
from urllib.parse import quote

from django.core.files.base import ContentFile
from django.db.models import Max

from ..models import MAX_PDF_MB, Series, SeriesFile
from .kzto import MB, fetch

GUARDO = 'https://guardo.ru'
RETTA = [
    (
        'Каталог Guardo Retta',
        '/downloads/Guardo_Retta-catalog-web-14-12-23.pdf',
    ),
    (
        'Паспорт Guardo Retta',
        (
            '/upload/iblock/555/tdntolkoq6xwczbnal49cgysk1ph0vzz/'
            'Passport-Guardo-Retta-20.06.2023.pdf'
        ),
    ),
]
TORRE = [
    ('Каталог Guardo Torre', '/downloads/Guardo_Torre_15-12-24-catalog.pdf'),
    (
        'Паспорт Guardo Torre',
        (
            '/upload/iblock/7d8/gwejr7q6hii54th8mb9760rh89uv2o7l/'
            'Passport-Guardo-Torre-2023.pdf'
        ),
    ),
]
PILON = [
    ('Каталог Guardo Pilon', '/downloads/Guardo_Pilon_catalog_2024.pdf'),
    (
        'Паспорт Guardo Pilon',
        (
            '/upload/iblock/c48/b4nvtxqaotpuhkwai3uc2o13tvkimfnq/'
            'Паспорт_GUARDO Pilon_04.09.2026.pdf'
        ),
    ),
]
FILES = {
    'guardo-retta-3p': RETTA,
    'guardo-retta-4p': RETTA,
    'guardo-retta-6p': RETTA,
    'guardo-retta-6sp': RETTA,
    'guardo-torre-3d': TORRE,
    'guardo-torre-4d': TORRE,
    'guardo-torre-6d': TORRE,
    'guardo-pilon': PILON,
}


@dataclass
class Summary:
    added: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    # адрес → имя файла в хранилище: второй серии — без новой загрузки
    stored: dict[str, str] = field(default_factory=dict)


def _url(path: str) -> str:
    return GUARDO + quote(path, safe='/%')


def _download(url: str, summary: Summary) -> bytes | None:
    try:
        data = fetch(url)
    except OSError as error:
        summary.errors.append(f'{url}: {error}')
        return None
    if len(data) > MAX_PDF_MB * MB:
        summary.errors.append(f'{url}: больше {MAX_PDF_MB} МБ')
        return None
    if not data.startswith(b'%PDF'):
        summary.errors.append(f'{url}: не PDF')
        return None
    return data


def import_series(series: Series, summary: Summary, *, dry_run: bool) -> None:
    """Файлы — в конец списка файлов серии, в порядке FILES."""
    existing = set(series.files.values_list('title', flat=True))
    end = series.files.aggregate(end=Max('position'))['end']
    position = 0 if end is None else end + 1
    for title, path in FILES.get(series.slug, []):
        if title in existing:
            summary.skipped += 1
            continue
        url = _url(path)
        item = SeriesFile(series=series, title=title, position=position)
        if url in summary.stored:
            item.file.name = summary.stored[url]
        else:
            data = _download(url, summary)
            if data is None:
                continue
            summary.lines.append(f'{title}: {len(data) // MB} МБ')
            if dry_run:
                summary.stored[url] = ''
                summary.added += 1
                position += 1
                continue
            item.file.save(
                path.rsplit('/', 1)[1], ContentFile(data), save=False
            )
            summary.stored[url] = item.file.name
        if not dry_run:
            item.save()
        summary.added += 1
        position += 1


def slugs_for(brand: str) -> list[str]:
    return list(FILES) if brand in {'guardo', 'all'} else []
