"""Витринные фото с сайтов заводов — первыми в галерее серии (решения
№ 164, 166).

- Guardo (guardo.ru): на странице модели — рендер на каждую высоту, в имени
  файла высота и положение (…-1800-mm-vysotoy-vertikalnoe-…). Берём по две
  высоты на положение, ближайшие к типичным (PREFERRED_MM). На страницах
  высот — цветные рендеры 4:3 (цвет и положение в имени файла) и схема
  подключений: по рендеру на цвет и положение и обе схемы встают в конец
  галереи, чтобы не сдвинуть фото карточек.
- КЗТО (kztoradiator.ru): витринные плитки разделов (/ellipse/, /quadrum/).
  Хороши только те, что в KZTO_TILES: остальные лежат лишь 410×530.
- Velar (velarwh.ru): превью и интерьерные рендеры — velar_photos.py.

Для разделённых серий положение в источнике определяет целевое исполнение.
Повторный запуск не дублирует: фото с тем же описанием уже есть — пропуск.
Pilon не берём: у него первым стоит фото, выбранное в админке вручную,
а рендеры на guardo.ru только белые.
"""

import io
import json
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from urllib.parse import quote, unquote, urljoin

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F, Max
from PIL import Image, UnidentifiedImageError

from apps.content.models import MAX_IMAGE_MB

from ..choices import Orientation
from ..models import Color, Series, SeriesImage
from .factory_editions import legacy_targets, registry
from .kzto import MB, absolute, fetch
from .velar_photos import COLOR_WORD, VELAR, VELAR_COLORS, VELAR_PHOTOS

GUARDO = 'https://guardo.ru/catalog/'
GUARDO_PAGES = {
    'guardo-retta-3p': 'trubchatye-radiatory-guardo-retta-3p-s-kvadratnym-profilem-30x30/',
    'guardo-retta-4p': 'trubchatye-radiatory-guardo-retta-4p-s-kvadratnym-profilem/',
    'guardo-retta-6p': 'trubchatye-radiatory-guardo-retta-6p-s-pryamougolnym-profilem/',
    'guardo-retta-6sp': 'trubchatye-radiatory-guardo-retta-6sp-s-pryamougolnym-profilem-30x60/',
    'guardo-torre-3d': 'trubchatye-radiatory-guardo-torre-3d-s-krugloy-truboy-32-mm/',
    'guardo-torre-4d': 'trubchatye-radiatory-guardo-torre-4d-s-krugloy-truboy-42-mm/',
    'guardo-torre-6d': 'trubchatye-radiatory-guardo-torre-6d-s-krugloy-truboy-60-mm/',
}
# Рендер 2x (1400×932) — адрес из srcset; высота и положение — в имени
GUARDO_RENDER = re.compile(
    r'(/upload/resize_cache/iblock/[^" ,]+?/1400_932_[^" ,/]+/'
    r'[^" ,/]*?-(\d+)-mm-vysotoy[^" ,/]*\.jpg)',
)
# Страница высоты — ссылка со страницы модели; на ней фото в 1440×960
GUARDO_ITEM = '<a[^>]+href="(/catalog/{}[^"]+/)"'
GUARDO_PICTURE = re.compile(r'data-src="([^"]+/1440_960_1/[^"]+\.jpe?g)"')
# Цвет рендера в имени файла: словом (Retta) или номером RAL (Torre)
GUARDO_COLORS = (
    ('RAL 9016', re.compile(r'white|9016', re.IGNORECASE)),
    ('RAL 9005', re.compile(r'black|9005', re.IGNORECASE)),
    ('RAL 7040', re.compile(r'grey|gray|7040', re.IGNORECASE)),
    ('RAL 1015', re.compile(r'bej|beige|1015', re.IGNORECASE)),
)
GUARDO_VERTICAL = re.compile(r'VER|vertical', re.IGNORECASE)
GUARDO_HORIZONTAL = re.compile(r'GOR|horizontal', re.IGNORECASE)
SCHEME = 'connection-'
# Две высоты на положение: самая ходовая и вторая — для разнообразия
PREFERRED_MM = {
    Orientation.VERTICAL: (1800, 1200),
    Orientation.HORIZONTAL: (450, 250),
}

KZTO = 'https://kztoradiator.ru/assets/manager/catalog/'
KZTO_TILES = {
    'kzto-ellipse-s-v': [('ELIPS147-1.jpg', 'v')],
    'kzto-ellipse-s-h': [('ELIPS.150.jpg', 'h')],
    'kzto-ellipse-p-v': [('ELIPS.167.jpg', 'v')],
    'kzto-ellipse-p-h': [('ELIPS.149.jpg', 'h')],
    'kzto-quadrum-30-v': [('quadrum-30-v-short.png', 'v')],
    'kzto-quadrum-50-v': [('q50v-cat.png', 'v')],
    'kzto-quadrum-neo-50-h': [('qneo50h-2.png', 'h')],
}

MAX_SIDE = 2000  # больше на сайте не нужно: PNG по 6 МБ ужимаем в JPEG
VERTICAL_FROM_MM = 900
POSITION_WORD = {'v': 'вертикальный', 'h': 'горизонтальный'}


@dataclass(frozen=True)
class Photo:
    url: str
    orientation: str
    height_mm: int | None = None
    kind: str = SeriesImage.Kind.PRODUCT
    color: str = ''  # код цвета (RAL 9016) — фото привязано к цвету
    label: str = ''  # слово в описании: цвет на фото
    last: bool = False  # в конец галереи, а не в начало


@dataclass
class Summary:
    added: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)


def _orientation(name: str, height: int, *, infer_position: bool) -> str:
    if 'vertikal' in name:
        return Orientation.VERTICAL
    if 'gorizont' in name:
        return Orientation.HORIZONTAL
    if not infer_position:
        return ''
    # У некоторых заводских рендеров в имени указана только высота радиатора.
    return (
        Orientation.VERTICAL
        if height >= VERTICAL_FROM_MM
        else Orientation.HORIZONTAL
    )


def guardo_renders(
    html: str, base: str, *, infer_position: bool = True
) -> list[Photo]:
    """Рендеры страницы модели: по две высоты на положение (PREFERRED_MM)."""
    found: dict[tuple[str, int], str] = {}
    for path, height in GUARDO_RENDER.findall(html):
        mm = int(height)
        orientation = _orientation(path, mm, infer_position=infer_position)
        if orientation:
            found.setdefault((orientation, mm), urljoin(base, path))
    chosen: list[Photo] = []
    for orientation, targets in PREFERRED_MM.items():
        heights = sorted({mm for o, mm in found if o == orientation})
        for target in targets:
            left = [
                mm
                for mm in heights
                if all(
                    p.height_mm != mm or p.orientation != orientation
                    for p in chosen
                )
            ]
            if not left:
                break
            mm = min(left, key=lambda h, t=target: (abs(h - t), h))
            chosen.append(Photo(found[orientation, mm], orientation, mm))
    return chosen


def guardo_extras(html: str, path: str, summary: Summary) -> list[Photo]:
    """Со страниц высот: по цветному рендеру на цвет и положение (без
    крупных планов, отзеркаленный — если другого нет) и схемы подключений.
    Всё — в конец галереи."""
    items = list(dict.fromkeys(re.findall(GUARDO_ITEM.format(path), html)))
    colored: dict[tuple[str, str], Photo] = {}
    schemes: dict[str, Photo] = {}
    for item in items:
        url = urljoin(GUARDO, item)
        try:
            page = fetch(url).decode('utf-8', 'replace')
        except OSError as error:
            summary.errors.append(f'{url}: {error}')
            continue
        for src in GUARDO_PICTURE.findall(page):
            photo = guardo_picture(urljoin(url, quote(src, safe='/%')))
            if photo is None:
                continue
            if photo.kind == SeriesImage.Kind.SCHEME:
                schemes.setdefault(photo.orientation, photo)
                continue
            key = (photo.orientation, photo.color)
            old = colored.get(key)
            if old is None or ('mirror' in old.url and 'mirror' not in src):
                colored[key] = photo
    order = [code for code, _ in GUARDO_COLORS]
    return [
        *sorted(
            colored.values(),
            key=lambda p: (p.orientation != 'v', order.index(p.color)),
        ),
        *(schemes[o] for o in ('v', 'h') if o in schemes),
    ]


def guardo_picture(url: str) -> Photo | None:
    """Цветной рендер или схема по имени файла; иначе None."""
    name = unquote(url.rsplit('/', 1)[1])
    vertical = GUARDO_VERTICAL.search(name)
    horizontal = GUARDO_HORIZONTAL.search(name)
    if name.startswith(SCHEME):
        orientation = 'h' if name.endswith('-gor.jpg') else 'v'
        return Photo(url, orientation, kind=SeriesImage.Kind.SCHEME, last=True)
    if 'zoom' in name or bool(vertical) == bool(horizontal):
        return None
    color = next((code for code, rx in GUARDO_COLORS if rx.search(name)), '')
    if not color:
        return None
    return Photo(
        url,
        'v' if vertical else 'h',
        color=color,
        label=color,
        last=True,
    )


def alt(series_name: str, photo: Photo) -> str:
    parts = [series_name]
    if photo.height_mm:
        parts.append(f'{photo.height_mm} мм')
    parts.append(POSITION_WORD[photo.orientation])
    if photo.kind == SeriesImage.Kind.INTERIOR:
        parts.append('в интерьере')
    if photo.kind == SeriesImage.Kind.SCHEME:
        parts.append('схема подключений')
    if photo.label:
        parts.append(photo.label)
    return ', '.join(parts)


def prepare(data: bytes) -> tuple[bytes, str, int, int]:
    """JPEG не больше MAX_SIDE; PNG с прозрачностью остаётся PNG."""
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        alpha = image.mode in {'RGBA', 'LA'} or 'transparency' in image.info
        if max(image.size) <= MAX_SIDE and image.format == 'JPEG':
            return data, 'jpg', *image.size
        image.thumbnail((MAX_SIDE, MAX_SIDE))
        out = io.BytesIO()
        if alpha:
            image.save(out, 'PNG', optimize=True)
            return out.getvalue(), 'png', *image.size
        image.convert('RGB').save(out, 'JPEG', quality=88, optimize=True)
        return out.getvalue(), 'jpg', *image.size


def photos_for(series: Series, summary: Summary) -> list[Photo]:
    parent = _parent_slug(series.slug)
    slug = parent or series.slug
    if slug in GUARDO_PAGES:
        page = GUARDO_PAGES[slug]
        url = GUARDO + page
        try:
            html = fetch(url).decode('utf-8', 'replace')
        except OSError as error:
            summary.errors.append(f'{url}: {error}')
            return []
        photos = guardo_renders(
            html,
            url,
            infer_position=not (parent or series.factory_orientation),
        )
        if not photos:
            summary.errors.append(
                f'{url}: рендеров не нашлось — сменилась вёрстка?'
            )
        return photos + guardo_extras(html, page, summary)
    if slug in VELAR_PHOTOS:
        return velar_photos(slug)
    return [Photo(KZTO + name, o) for name, o in KZTO_TILES.get(slug, [])]


def velar_photos(slug: str) -> list[Photo]:
    """Товарные — первыми, внутри — вертикальные, потом горизонтальные."""
    rows = sorted(
        VELAR_PHOTOS[slug],
        key=lambda row: (row[2] != 'p', row[1] != Orientation.VERTICAL),
    )
    return [
        Photo(
            VELAR + name,
            orientation,
            kind=(
                SeriesImage.Kind.PRODUCT
                if kind == 'p'
                else SeriesImage.Kind.INTERIOR
            ),
            color=VELAR_COLORS.get(color, ''),
            label=COLOR_WORD.get(color, ''),
        )
        for name, orientation, kind, color in rows
    ]


def import_series(series: Series, summary: Summary, *, dry_run: bool) -> None:
    """Новые фото — в начало галереи (с last — в конец), в порядке
    photos_for; уже загруженные (то же описание) — пропуск, их место не
    трогаем."""
    existing = set(series.images.values_list('image_alt', flat=True))
    sources = {
        url
        for primary, aliases in series.images.values_list(
            'source_url', 'source_aliases'
        )
        for url in (primary, *aliases)
    }
    legacy_name = series.name
    orientation = series.factory_orientation
    parent = _parent_slug(series.slug)
    if parent:
        entry = registry()['parents'][parent]
        legacy_name = entry['name']
        expected = next(
            value['orientation']
            for value in entry['targets'].values()
            if value['slug'] == series.slug
        )
        if orientation and orientation != expected:
            summary.errors.append(f'{series.slug}: неверное положение серии')
            return
        orientation = expected
    fresh: list[tuple[Photo, bytes, str, int, int]] = []
    for photo in photos_for(series, summary):
        if orientation and photo.orientation != orientation:
            continue
        text = alt(series.name, photo)
        if (
            photo.url in sources
            or text in existing
            or alt(legacy_name, photo) in existing
        ):
            summary.skipped += 1
            continue
        try:
            data = fetch(photo.url)
            if len(data) > MAX_IMAGE_MB * MB:
                summary.errors.append(f'{photo.url}: больше {MAX_IMAGE_MB} МБ')
                continue
            fresh.append((photo, *prepare(data)))
        except (OSError, UnidentifiedImageError) as error:
            summary.errors.append(f'{photo.url}: {error}')
            continue
        sources.add(photo.url)
        existing.add(text)
        summary.lines.append(f'{text}: {fresh[-1][3]}×{fresh[-1][4]}')
    if not fresh or dry_run:
        summary.added += len(fresh)
        return
    colors = {
        c.code: c
        for c in Color.objects.filter(code__in={p.color for p, *_ in fresh})
    }
    head = [f for f in fresh if not f[0].last]
    tail = [f for f in fresh if f[0].last]
    with transaction.atomic():
        series.images.update(position=F('position') + len(head))
        end = series.images.aggregate(end=Max('position'))['end']
        start = 0 if end is None else end + 1
        positions = [*range(len(head)), *range(start, start + len(tail))]
        for position, (photo, data, ext, width, height) in zip(
            positions,
            head + tail,
            strict=True,
        ):
            image = SeriesImage(
                series=series,
                kind=photo.kind,
                color=colors.get(photo.color),
                source_url=photo.url,
                image_alt=alt(series.name, photo),
                position=position,
            )
            image.image.save(
                f'{series.slug}-{position}.{ext}',
                ContentFile(data),
                save=False,
            )
            # Размеры — после записи файла: ImageField при записи
            # перечитывает их из хранилища и в S3 получает пустые. Пустые
            # размеры — и каждый запрос каталога скачивает файл заново
            image.image_width, image.image_height = width, height
            image.save()
    summary.added += len(fresh)


def slugs_for(brand: str) -> list[str]:
    pages = {
        'guardo': list(GUARDO_PAGES),
        'kzto': list(KZTO_TILES),
        'velar': list(VELAR_PHOTOS),
    }
    return pages.get(
        brand, [slug for slugs in pages.values() for slug in slugs]
    )


@cache
def _parents_by_edition():
    return {
        child: parent
        for parent, children in legacy_targets().items()
        for child in children
    }


def _parent_slug(slug):
    return _parents_by_edition().get(slug)


@cache
def _checked_photo_sources():
    data_dir = Path(__file__).resolve().parents[1] / 'data'
    factory = json.loads((data_dir / 'factory_media_sources.json').read_text())
    kzto = json.loads((data_dir / 'kzto_media_sources.json').read_text())
    sources = {row['series']: row.get('photos', []) for row in factory['rows']}
    for row in kzto['rows']:
        slug = row['series_slug']
        urls = [
            absolute(url) for url in [row['tile_url'], *row['gallery']] if url
        ]
        urls.extend(KZTO + name for name, _ in KZTO_TILES.get(slug, []))
        sources[slug] = [{'url': url} for url in urls]
    return sources


def confirmed_photo_target(image, target):
    """Подтверждение исполнения по проверенному источнику старого фото."""
    urls = {image.source_url, *image.source_aliases} - {''}
    digest = image.source_sha256
    has_source = bool(urls or digest)
    slug = target.slug
    for source in _checked_photo_sources().get(slug, []):
        if source['url'] in urls or (
            digest and digest == source.get('sha256')
        ):
            return True
        if (
            not has_source
            and image.image_alt == source.get('legacy_alt')
            and image.kind == source.get('kind')
        ):
            return True
    # Рендеры с сайта Velar до разделения могли сохраняться без URL.
    root = _parent_slug(slug)
    if root not in VELAR_PHOTOS:
        return False
    name = registry()['parents'][root]['name']
    return any(
        photo.orientation == target.factory_orientation
        and photo.kind == image.kind
        and (
            photo.url in urls
            or (not has_source and alt(name, photo) == image.image_alt)
        )
        for photo in velar_photos(root)
    )
