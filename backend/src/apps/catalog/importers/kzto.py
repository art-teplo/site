"""Импорт КЗТО с сайта завода kztoradiator.ru (решение № 151).

Варианты, размеры, мощность, цены в RUB и фото — из YML-фида; описание,
параметры и документы серии — со страницы серии. Категория фида — серия
завода; H- и V-исполнения одной модели у нас одна серия с полем
«Положение». Цены в BYN считает ночная задача курсов с наценкой бренда.

Повторный импорт обновляет варианты и цены, пропавшие из фида варианты
скрывает. У серии заполняет только пустые поля (описание, материал,
давление, гарантию, тип), фото и документы — только если их ещё нет:
правки менеджеров не перетираются.
"""

import io
import logging
import re

# expat не тянет внешние сущности и режет «billion laughs»; фид — завода
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, UnidentifiedImageError

from apps.content.models import MAX_IMAGE_MB, Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend

from ..choices import Connection, Currency, Heating, Orientation
from ..models import (
    MAX_PDF_MB,
    Brand,
    Category,
    Series,
    SeriesFile,
    SeriesImage,
    Subcategory,
    Variant,
)
from ..photos import trim_white
from ..pricing import recalculate
from .kzto_page import Page, parse_page

logger = logging.getLogger(__name__)

SITE = 'https://kztoradiator.ru/'
FEED_URL = urljoin(SITE, 'yml-feed.xml')
# Страница серии по id категории фида (это id ресурса MODX)
PAGE_URL = urljoin(SITE, 'index.php?id={}')
USER_AGENT = 'Mozilla/5.0 (compatible; catalog-import)'
TIMEOUT = 60

BRAND_SLUG = 'kzto'
BRAND_NAME = 'КЗТО'
MB = 1024 * 1024
BATCH_SIZE = 1000
MAX_IMAGES = 6
MAX_FILES = 6
# Вытянутое по горизонтали фото — интерьер, остальное — товар
INTERIOR_RATIO = Decimal('1.2')
# Документы серии; общие файлы сайта (условные обозначения, приложения к
# паспортам, видео, каталоги) не берём
DOCUMENTS = re.compile(
    r'^(паспорт|монтажн|сертификат|декларац|рекомендац|руководство по монт)',
    re.IGNORECASE,
)

RADIATOR = 'radiator'
CONVECTOR = 'convector'
GRILLE = 'grille'


@dataclass(frozen=True)
class Target:
    """Наша серия для категории фида."""

    slug: str
    name: str
    category: str
    subcategory: str
    kind: str = RADIATOR
    orientation: str = ''


def _radiator(slug, name, subcategory='trubchatye', orientation=''):
    return Target(slug, name, 'radiatory', subcategory, RADIATOR, orientation)


def _design(slug, name, orientation=''):
    return _radiator(slug, name, 'dizajn', orientation)


def _in_floor(slug, name, kind=CONVECTOR):
    return Target(slug, name, 'konvektory', 'vnutripolnye', kind)


def _on_floor(slug, name):
    return Target(slug, name, 'konvektory', 'napolnye', CONVECTOR)


H, V = Orientation.HORIZONTAL, Orientation.VERTICAL

# Категория фида → серия. Состав — бриф, «Бренды на старте» (№ 122)
TARGETS: dict[str, Target] = {
    'Гармония': _radiator('kzto-garmoniya', 'Гармония'),
    'Гармония А20': _radiator('kzto-garmoniya-a20', 'Гармония А20'),
    'Гармония А25 N': _radiator('kzto-garmoniya-a25-n', 'Гармония А25 N'),
    'Гармония С25 N': _radiator('kzto-garmoniya-s25-n', 'Гармония С25 N'),
    'Гармония А40': _radiator('kzto-garmoniya-a40', 'Гармония А40'),
    'Гармония С40': _radiator('kzto-garmoniya-s40', 'Гармония С40'),
    'РС': _radiator('kzto-rs', 'РС'),
    'РСК': _radiator('kzto-rsk', 'РСК'),
    'Соло В': _radiator('kzto-solo', 'Соло', orientation=V),
    'Соло Г': _radiator('kzto-solo', 'Соло', orientation=H),
    'Параллели В': _radiator('kzto-paralleli', 'Параллели', orientation=V),
    'Параллели Г': _radiator('kzto-paralleli', 'Параллели', orientation=H),
    'Quadrum 30 V': _design('kzto-quadrum-30', 'Quadrum 30', V),
    'Quadrum 30 H': _design('kzto-quadrum-30', 'Quadrum 30', H),
    'Quadrum 40 V': _design('kzto-quadrum-40', 'Quadrum 40', V),
    'Quadrum 40 H': _design('kzto-quadrum-40', 'Quadrum 40', H),
    'Quadrum 50 V': _design('kzto-quadrum-50', 'Quadrum 50', V),
    'Quadrum 50 H': _design('kzto-quadrum-50', 'Quadrum 50', H),
    'Quadrum 60 V': _design('kzto-quadrum-60', 'Quadrum 60', V),
    'Quadrum 60 H': _design('kzto-quadrum-60', 'Quadrum 60', H),
    'QUADRUM NEO 50 V': _design('kzto-quadrum-neo-50', 'Quadrum NEO 50', V),
    'QUADRUM NEO 50 H': _design('kzto-quadrum-neo-50', 'Quadrum NEO 50', H),
    'BATARÌA': _design('kzto-bataria', 'BATARÌA'),
    'BATARÌA Retro': _design('kzto-bataria-retro', 'BATARÌA Retro'),
    'Ellipse P V': _design('kzto-ellipse-p', 'Ellipse P', V),
    'Ellipse P H': _design('kzto-ellipse-p', 'Ellipse P', H),
    'Ellipse S V': _design('kzto-ellipse-s', 'Ellipse S', V),
    'Ellipse S H': _design('kzto-ellipse-s', 'Ellipse S', H),
    'Бриз': _in_floor('kzto-briz', 'Бриз'),
    'Бриз Нерж': _in_floor('kzto-briz-nerzh', 'Бриз Нерж'),
    'Бриз В': _in_floor('kzto-briz-v', 'Бриз В'),
    'Бриз В Нерж': _in_floor('kzto-briz-v-nerzh', 'Бриз В Нерж'),
    'Бриз В TURBO': _in_floor('kzto-briz-v-turbo', 'Бриз В TURBO'),
    'Бриз В TURBO Нерж': _in_floor(
        'kzto-briz-v-turbo-nerzh',
        'Бриз В TURBO Нерж',
    ),
    'Решетка Бриз': _in_floor('kzto-reshetka-briz', 'Решётка Бриз', GRILLE),
    'Элегант': _on_floor('kzto-elegant', 'Элегант'),
    'Элегант Мини': _on_floor('kzto-elegant-mini', 'Элегант Мини'),
    'Элегант Плюс': _on_floor('kzto-elegant-plyus', 'Элегант Плюс'),
    'Элегант В': _on_floor('kzto-elegant-v', 'Элегант В'),
}
# Не продаём отдельно или не берём на старте (№ 122)
SKIPPED = frozenset(
    {
        'Комплектующие',
        'Крышки для защиты приборов',
        'Окантовка БРИЗ',
        'Зеркало',
        'Зеркало А40',
        'Зеркало П',
        'Зеркало С',
        'Завалинка РС',
        'Завалинка Гармония',
    },
)
CATEGORY_NAMES = {'radiatory': 'Радиаторы', 'konvektory': 'Конвекторы'}

# Параметры фида
AXIS = 'Межцентр. размер, мм'
FULL_HEIGHT = 'Габаритная высота, мм (без учета ножек)'
HEIGHT = 'Высота, мм'
WIDTH = 'Ширина, мм'
LENGTH = 'Длина, мм'
DEPTH = 'Глубина, мм'
SECTIONS = 'Число секций'
COLUMNS = 'Число колонок по глубине'
POWER = 'Паспортная мощность при Δt70, Вт'
EXPONENT = 'Степенной коэффициент n'
WEIGHT = 'Вес, кг'
VOLUME = 'Объем, л'
PRESSURE = 'Макс. рабочее давление, бар.'
WARRANTY = 'Гарантия, лет'
DEVICE_HEIGHT = 'Высота прибора H, мм'
DEVICE_WIDTH = 'Ширина прибора В, мм'
DEVICE_LENGTH = 'Длина прибора L, мм'
EXCHANGERS = 'Количество теплообменников'
FANS = 'Количество вентиляторов'
VOLTAGE = 'Напряжение, В'
GRILLE_COVER = 'Покрытие решетки'
GRILLE_GAP = 'Ширина просвета между планками'
MATERIAL = 'Материал'
# «Способ подключения», «Подключение», «Подключение (Настенное исполнение)»
CONNECTION_PARAMS = ('способ подключения', 'подключение')

FAN = 'с вентилятором'
NO_FAN = 'без вентилятора'
GRILLE_TYPE = re.compile(r'решетка\s+(\w+)', re.IGNORECASE)

VARIANT_FIELDS = (
    'connection',
    'height_mm',
    'width_mm',
    'depth_mm',
    'length_mm',
    'axis_mm',
    'sections',
    'power_w',
    'tubes',
    'orientation',
    'price',
    'currency',
    'is_active',
    'attrs',
)

# В фиде бывает адрес без слэша после домена: kztoradiator.ruassets/…
GLUED_HOST = re.compile(r'^(https?://kztoradiator\.ru)(?=[^/:?#])')
FETCH_FAILED = 'не скачать {}: {}'
BAD_FEED = 'фид не разобрать: {}'
NO_OFFERS = 'в фиде нет shop/offers'
FOREIGN_SERIES = 'серия «{}» уже есть у другого бренда'
BAD_IMAGE = 'не картинка: {}'
BAD_PDF = 'не PDF: {}'
TOO_BIG = 'больше {} МБ: {}'


class FeedError(Exception):
    """Фид не скачать или не разобрать."""


@dataclass
class Offer:
    id: str
    category: str
    name: str
    model: str
    price: Decimal | None
    available: bool
    pictures: list[str]
    params: dict[str, str]

    def number(self, *names: str) -> Decimal | None:
        """Первый заполненный параметр из names числом: «1,28» и «1.28»."""
        for name in names:
            text = (self.params.get(name) or '').strip().replace(',', '.')
            if not text:
                continue
            try:
                value = Decimal(text)
            except InvalidOperation:
                continue
            if value.is_finite():
                return value
        return None

    def integer(self, *names: str) -> int | None:
        value = self.number(*names)
        if value is None or value < 0:
            return None
        return int(value.to_integral_value(ROUND_HALF_UP))


@dataclass
class SeriesResult:
    series: Series
    created: bool
    offers: int
    filled: list[str] = field(default_factory=list)
    images: int = 0
    files: int = 0


@dataclass
class Summary:
    offers: int = 0
    series: list[SeriesResult] = field(default_factory=list)
    created: int = 0
    updated: int = 0
    hidden: int = 0
    # категория фида → вариантов: не берём / новая, нет в TARGETS
    skipped: Counter = field(default_factory=Counter)
    unknown: Counter = field(default_factory=Counter)
    # повтор артикула в фиде: (артикул, чем заменён)
    renamed: list[tuple[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def fetch(url: str) -> bytes:
    """GET с адресом, где кириллица и пробелы закодированы."""
    parts = urlsplit(url)
    path = quote(unquote(parts.path), safe='/')
    query = f'?{parts.query}' if parts.query else ''
    safe_url = f'{parts.scheme}://{parts.netloc}{path}{query}'
    request = Request(safe_url, headers={'User-Agent': USER_AGENT})  # noqa: S310
    with urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
        return response.read()


def absolute(url: str) -> str:
    """Полный адрес файла завода: относительный — от корня сайта."""
    return urljoin(SITE, GLUED_HOST.sub(r'\1/', url))


def read_feed(source: str) -> bytes:
    try:
        if source.startswith(('http://', 'https://')):
            return fetch(source)
        return Path(source).read_bytes()
    except OSError as error:
        raise FeedError(FETCH_FAILED.format(source, error)) from error


def parse_feed(data: bytes) -> tuple[dict[str, str], list[Offer]]:
    """Категории фида (id → название) и предложения."""
    try:
        root = ET.fromstring(data)  # noqa: S314
    except ET.ParseError as error:
        raise FeedError(BAD_FEED.format(error)) from error
    shop = root.find('shop')
    if shop is None or shop.find('offers') is None:
        raise FeedError(NO_OFFERS)
    categories = {
        c.get('id'): (c.text or '').strip()
        for c in shop.iterfind('categories/category')
    }
    offers = []
    for item in shop.iterfind('offers/offer'):
        category_id = (item.findtext('categoryId') or '').strip()
        price = (item.findtext('price') or '').strip()
        try:
            value = Decimal(price) if price else None
        except InvalidOperation:
            value = None
        offers.append(
            Offer(
                id=item.get('id') or '',
                category=category_id,
                name=' '.join((item.findtext('name') or '').split()),
                model=(item.findtext('model') or '').strip(),
                price=value if value and value > 0 else None,
                available=item.get('available') != 'false',
                pictures=[
                    p.text.strip()
                    for p in item.iterfind('picture')
                    if p.text and p.text.strip()
                ],
                params={
                    p.get('name'): (p.text or '').strip()
                    for p in item.iterfind('param')
                },
            ),
        )
    return categories, offers


def import_kzto(
    feed: str = FEED_URL,
    *,
    pages: bool = True,
    media: bool = True,
    publish: bool = False,
    dry_run: bool = False,
) -> Summary:
    """Весь импорт: данные одной транзакцией, потом фото и документы
    (по сети, по одной серии). dry_run — без записи и без скачивания
    фото и документов; кэш фронта сбрасывается один раз в конце."""
    categories, offers = parse_feed(read_feed(feed))
    summary = Summary(offers=len(offers))
    grouped: dict[str, list[Offer]] = defaultdict(list)
    feed_categories: dict[str, list[str]] = defaultdict(list)
    for offer in offers:
        name = categories.get(offer.category, offer.category)
        target = TARGETS.get(name)
        if target is None:
            bucket = summary.skipped if name in SKIPPED else summary.unknown
            bucket[name] += 1
            continue
        grouped[target.slug].append(offer)
        if offer.category not in feed_categories[target.slug]:
            feed_categories[target.slug].append(offer.category)
    targets_of = {
        cid: TARGETS[categories[cid]]
        for cid in categories
        if categories[cid] in TARGETS
    }

    loaded, by_category = {}, {}
    if pages:
        for slug, ids in feed_categories.items():
            loaded[slug] = _pages(summary, ids, by_category)

    with muted_revalidation():
        with transaction.atomic():
            connections = {
                cid: _connection(target, by_category.get(cid))
                for cid, target in targets_of.items()
            }
            saved = _save(
                summary,
                grouped,
                targets_of,
                loaded,
                connections,
                publish=publish,
            )
            if dry_run:
                transaction.set_rollback(True)
        if media and not dry_run:
            for result in summary.series:
                _media(summary, result, grouped[result.series.slug], loaded)
    if not dry_run and saved:
        revalidate_frontend.delay(Tag.CATALOG)
    return summary


def _pages(summary: Summary, ids: list[str], by_category) -> list[Page]:
    result = []
    for category_id in ids:
        url = PAGE_URL.format(category_id)
        try:
            html = fetch(url).decode('utf-8', errors='replace')
        except OSError as error:
            summary.errors.append(FETCH_FAILED.format(url, error))
            continue
        page = parse_page(html)
        by_category[category_id] = page
        result.append(page)
    return result


def _connection(target: Target, page: Page | None) -> str:
    """Базовое подключение радиатора — первое в «Способе подключения»
    страницы серии; без страницы — по положению: у горизонтальных КЗТО
    нижнее по краям, у остальных боковое. У конвекторов — нет."""
    if target.kind != RADIATOR:
        return ''
    text = ''
    if page is not None:
        text = next(
            (
                value
                for name, value in page.params
                if name.lower().startswith(CONNECTION_PARAMS)
            ),
            '',
        )
    base = re.split(r'[;,(]', text.lower(), maxsplit=1)[0]
    if 'боков' in base:
        return Connection.SIDE
    if 'разнес' in text.lower().split(';')[0]:
        return Connection.BOTTOM_ENDS
    if target.orientation == Orientation.HORIZONTAL:
        return Connection.BOTTOM_ENDS
    return Connection.SIDE


def _save(
    summary,
    grouped,
    targets_of,
    loaded,
    connections,
    *,
    publish,
) -> bool:
    if not grouped:
        return False
    brand, _ = Brand.objects.get_or_create(
        slug=BRAND_SLUG,
        defaults={'name': BRAND_NAME, 'is_published': False},
    )
    existing = {
        (variant.article, variant.connection): variant
        for variant in Variant.objects.filter(brand=brand)
    }
    seen_articles: set[str] = set()
    kept: set[tuple[str, str]] = set()
    for slug, offers in grouped.items():
        target = targets_of[offers[0].category]
        series, created = Series.objects.get_or_create(
            slug=slug,
            defaults={
                'brand': brand,
                'category': _category(target.category),
                'name': target.name,
                'is_published': publish,
                'heating': Heating.WATER,
            },
        )
        if series.brand_id != brand.pk:
            summary.errors.append(FOREIGN_SERIES.format(slug))
            continue
        result = SeriesResult(series, created, len(offers))
        summary.series.append(result)
        _fill_series(result, target, offers, loaded.get(slug, []))
        kept |= _save_variants(
            summary,
            series,
            offers,
            targets_of,
            connections,
            existing,
            seen_articles,
        )
    hidden = [
        variant.pk
        for key, variant in existing.items()
        if key not in kept and variant.is_active
    ]
    Variant.objects.filter(pk__in=hidden).update(is_active=False)
    summary.hidden = len(hidden)
    recalculate(Variant.objects.filter(brand=brand))
    return True


def _category(slug: str) -> Category:
    category, _ = Category.objects.get_or_create(
        slug=slug,
        defaults={'name': CATEGORY_NAMES[slug], 'is_published': False},
    )
    return category


def _most_common(offers, name: str) -> int | None:
    values = Counter(o.integer(name) for o in offers)
    values.pop(None, None)
    return values.most_common(1)[0][0] if values else None


def _fill_series(result: SeriesResult, target, offers, pages: list[Page]):
    """Заполняет пустые поля серии; заполненные — правка менеджера."""
    series = result.series
    changed = {}
    if series.subcategory_id is None:
        changed['subcategory'] = Subcategory.objects.filter(
            slug=target.subcategory,
            category=series.category,
        ).first()
    if series.pressure_bar is None:
        changed['pressure_bar'] = _most_common(offers, PRESSURE)
    if series.warranty_years is None:
        changed['warranty_years'] = _most_common(offers, WARRANTY)
    if pages:
        main = next((p for p in pages if p.description), pages[0])
        if not series.material:
            material = next(
                (p.param(MATERIAL) for p in pages if p.param(MATERIAL)),
                '',
            )
            changed['material'] = material[:100]
        if not series.description.strip():
            changed['description'] = main.html()
    for name, value in changed.items():
        if value:
            setattr(series, name, value)
            result.filled.append(name)
    if result.filled:
        series.save()


def _save_variants(
    summary,
    series,
    offers,
    targets_of,
    connections,
    existing,
    seen,
):
    new, changed, kept = [], [], set()
    for offer in offers:
        article = offer.model or offer.name
        if article in seen:
            # В фиде бывает один артикул у двух размеров (Batarìa 2-500-7
            # и 2-500-49): второй — по названию, иначе он затрёт первый
            summary.renamed.append((article, offer.name))
            article = offer.name
        seen.add(article)
        connection = connections.get(offer.category, '')
        key = (article[:100], connection)
        kept.add(key)
        target = targets_of[offer.category]
        values = _values(offer, target)
        values['connection'] = connection
        variant = existing.get(key)
        if variant is None and connection:
            # Вариант, записанный раньше без подключения, — тот же товар
            variant = existing.pop((key[0], ''), None)
            if variant is not None:
                existing[key] = variant
        if variant is not None:
            values['attrs'] = {**variant.attrs, **values['attrs']}
            if variant.series_id != series.pk:
                # Вариант, перенесённый менеджером в другую серию, не трогаем
                continue
            if any(getattr(variant, k) != v for k, v in values.items()):
                for name, value in values.items():
                    setattr(variant, name, value)
                changed.append(variant)
            continue
        variant = Variant(
            series=series,
            brand_id=series.brand_id,
            article=key[0],
            **values,
        )
        existing[key] = variant
        new.append(variant)
    Variant.objects.bulk_create(new, batch_size=BATCH_SIZE)
    Variant.objects.bulk_update(changed, VARIANT_FIELDS, batch_size=BATCH_SIZE)
    summary.created += len(new)
    summary.updated += len(changed)
    return kept


def _decimal_attr(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _values(offer: Offer, target: Target) -> dict:
    attrs = {
        'weight_kg': _decimal_attr(offer.number(WEIGHT)),
        'volume_l': _decimal_attr(offer.number(VOLUME)),
        'exponent_n': _decimal_attr(offer.number(EXPONENT)),
    }
    values = {
        'height_mm': None,
        'width_mm': None,
        'depth_mm': None,
        'length_mm': None,
        'axis_mm': None,
        'sections': None,
        'power_w': offer.integer(POWER),
        'tubes': None,
        'orientation': target.orientation,
        'price': offer.price,
        'currency': Currency.RUB,
        'is_active': offer.available,
    }
    if target.kind == RADIATOR:
        values |= {
            'height_mm': offer.integer(FULL_HEIGHT, HEIGHT),
            'width_mm': offer.integer(LENGTH),
            'depth_mm': offer.integer(DEPTH),
            'axis_mm': offer.integer(AXIS),
            'sections': offer.integer(SECTIONS),
            'tubes': offer.integer(COLUMNS),
        }
    elif target.kind == CONVECTOR:
        values |= {
            'height_mm': offer.integer(HEIGHT, DEVICE_HEIGHT),
            'width_mm': offer.integer(WIDTH, DEVICE_WIDTH),
            'length_mm': offer.integer(LENGTH, DEVICE_LENGTH),
        }
        fans = offer.integer(FANS)
        voltage = offer.integer(VOLTAGE)
        attrs |= {
            'fan': FAN if fans else NO_FAN,
            'voltage': f'{voltage} В' if voltage else None,
            'exchangers': offer.integer(EXCHANGERS),
        }
    else:
        values |= {
            'width_mm': offer.integer(WIDTH),
            'length_mm': offer.integer(LENGTH),
        }
        kind = GRILLE_TYPE.search(offer.name)
        gap = offer.integer(GRILLE_GAP)
        attrs |= {
            'grille_type': kind.group(1).lower() if kind else None,
            'grille_material': offer.params.get(GRILLE_COVER) or None,
            'grille_step': f'{gap} мм' if gap else None,
        }
    values['attrs'] = {k: v for k, v in attrs.items() if v is not None}
    return values


# --- фото и документы ---


def _media(summary, result: SeriesResult, offers, loaded):
    series = result.series
    if not series.images.exists():
        pictures = list(
            dict.fromkeys(url for offer in offers for url in offer.pictures),
        )
        for position, url in enumerate(pictures[:MAX_IMAGES], start=1):
            result.images += _save_image(summary, series, url, position)
    if not series.files.exists():
        documents = [
            document
            for page in loaded.get(series.slug, [])
            for document in page.documents
            if DOCUMENTS.match(document.title)
            and document.url.lower().endswith('.pdf')
        ]
        unique = list({d.url: d for d in documents}.values())
        for position, document in enumerate(unique[:MAX_FILES], start=1):
            result.files += _save_file(summary, series, document, position)


def _download(summary, url: str, limit_mb: int) -> bytes | None:
    try:
        data = fetch(url)
    except OSError as error:
        summary.errors.append(FETCH_FAILED.format(url, error))
        return None
    if len(data) > limit_mb * MB:
        summary.errors.append(TOO_BIG.format(limit_mb, url))
        return None
    return data


def _file_name(url: str) -> str:
    return PurePosixPath(unquote(urlsplit(url).path)).name


def _save_image(summary, series, url, position) -> int:
    data = _download(summary, absolute(url), MAX_IMAGE_MB)
    if data is None:
        return 0
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            image_format = image.format
    except UnidentifiedImageError, OSError:
        summary.errors.append(BAD_IMAGE.format(url))
        return 0
    if image_format not in ('JPEG', 'PNG', 'WEBP'):
        summary.errors.append(BAD_IMAGE.format(url))
        return 0
    # Вертикальный кадр, дополненный белым до горизонтального, — без полей
    trimmed = trim_white(data)
    if trimmed:
        data, width, height = trimmed.data, trimmed.width, trimmed.height
    wide = Decimal(width) > Decimal(height) * INTERIOR_RATIO
    image = SeriesImage(
        series=series,
        kind=SeriesImage.Kind.INTERIOR if wide else SeriesImage.Kind.PRODUCT,
        image_alt=f'{series.name} — фото {position}',
        position=position,
    )
    image.image.save(_file_name(url), ContentFile(data), save=False)
    # Размеры — после записи файла: ImageField при записи перечитывает их из
    # хранилища (в S3 — пустые), а без них каждый запрос каталога скачивает
    # файл заново
    image.image_width, image.image_height = width, height
    image.save()
    return 1


def _save_file(summary, series, document, position) -> int:
    url = absolute(document.url)
    data = _download(summary, url, MAX_PDF_MB)
    if data is None:
        return 0
    if not data.startswith(b'%PDF'):
        summary.errors.append(BAD_PDF.format(url))
        return 0
    item = SeriesFile(
        series=series,
        title=document.title[:150],
        position=position,
    )
    item.file.save(_file_name(url), ContentFile(data), save=False)
    item.save()
    return 1
