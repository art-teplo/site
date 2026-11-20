"""Импорт прайса Velar: профильные (дизайн-) радиаторы, xlsx завода.

Лист — исполнение модели (P30 V, P30 H…); V и H одной модели у нас одна
серия с полем «Положение», как у КЗТО. В строке листа — один размер и до
пяти подключений: пары «Наименование / Артикул», код подключения — в
артикуле (Velar P30 270 V - 2 БП RAL9016). Цена — «Итоговая стоимость»
(«Цена» с «Размером скидки» листа), RUB; в BYN её переводит pricing.

Повторный импорт обновляет варианты и цены, пропавшие из файла скрывает
(только у серий этого прайса — трубчатые Velar придут другим файлом).
У серии заполняет только пустые поля; группы цветов создаёт, если их нет.
"""

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend

from ..choices import Connection, Currency, Heating, Mount, Orientation
from ..models import (
    Brand,
    Category,
    Color,
    ColorGroup,
    Series,
    Subcategory,
    Variant,
)
from ..pricing import recalculate
from .factory_editions import (
    active_split_parents,
    route_velar,
    validate_split_parents,
)
from .product_families import assign_family, import_traits
from .velar_text import describe
from .xlsx import ANY_RAL_GROUP, BASE_GROUP, PriceFileError, _open

BRAND_SLUG = 'velar'
BRAND_NAME = 'Velar'
CATEGORY = 'radiatory'
CATEGORY_NAME = 'Радиаторы'
SUBCATEGORY = 'dizajn'
MATERIAL = 'Сталь'
BASE_COLOR = 'RAL 9016'
BATCH_SIZE = 1000
KOPECK = Decimal('0.01')

V, H = Orientation.VERTICAL, Orientation.HORIZONTAL


@dataclass(frozen=True)
class Sheet:
    slug: str
    name: str
    orientation: str
    mount: str = ''


def _model(code: str, name: str, *sheets: tuple[str, str]):
    slug = f'velar-{code}'
    return {title: Sheet(slug, name, o) for title, o in sheets}


SHEETS: dict[str, Sheet] = {
    **_model('p30', 'Velar P30', ('P30 V', V), ('P30 H', H)),
    **_model('p60', 'Velar P60', ('P60 V', V), ('P60 H', H)),
    **_model('s', 'Velar S', ('S V', V), ('S H', H)),
    **_model('sp', 'Velar SP', ('SP V', V), ('SP H', H)),
    **_model('q40', 'Velar Q40', ('Q40 V', V)),
    **_model('q60', 'Velar Q60', ('Q60 V', V), ('Q60 H', H)),
    **_model('q80', 'Velar Q80', ('Q80 V', V), ('Q80 H', H)),
    **_model('r32', 'Velar R32', ('R32 V', V), ('R32 H', H)),
    **_model('r42', 'Velar R42', ('R42 V', V), ('R42 H', H)),
    **_model('r89', 'Velar R89', ('R89 V', V), ('R89 H', H)),
    **_model('rt1', 'Velar RT1', ('RT1', V)),
    **_model('rt2', 'Velar RT2', ('RT2', V)),
    **_model('rt1w', 'Velar RT1W', ('RT1W', V)),
    **_model('rt2w', 'Velar RT2W', ('RT2W', V)),
    **_model('qt1', 'Velar QT1', ('QT1', V)),
    **_model('qt2', 'Velar QT2', ('QT2', V)),
}
# Напольные — три модели на одном листе, серия — по колонке «Модель»
FLOOR_SHEET = 'Напольные'
FLOOR_MODELS = {
    f'VELAR {code}': Sheet(
        f'velar-{code.lower()}', f'Velar {code}', H, Mount.FLOOR
    )
    for code in ('P200', 'P300', 'Q500')
}
# P60-30: у одного артикула по четыре ширины, итоговые цены E-1040
# перепутаны местами, на сайте завода модели нет — до уточнения не берём
SKIPPED = frozenset({'P60-30'})

NAME = 'Наименование'
ARTICLE = 'Артикул'
HEIGHT = 'Высота'
SECTIONS = 'Кол-во секций'
LENGTH = 'Длина'
POWER = 'Мощность'
DEPTH = 'Глубина'
AXIS_N = 'N'  # межосевое по высоте — у бокового подключения
AXIS_E = 'E'  # межосевое по длине — у нижнего по краям
TOTAL = 'Итоговая стоимость'
MODEL = 'Модель'
COLUMNS = (HEIGHT, LENGTH, TOTAL)
# «Покраска только в цвета МУАР!!!» — любой RAL не предлагаем
ONLY_PAINT = re.compile(r'только', re.IGNORECASE)

# Код подключения в артикуле: БП — боковое, ЛП — нижнее по краям,
# Л50 / П50 / 050 — нижнее левое, правое, центральное с межосевым 50 мм
CONNECTION_CODE = re.compile(r'\s(БП|ЛП|[ЛП0]\d{2,3})(?:\s|$)')
BOTTOM = {
    'Л': Connection.BOTTOM_LEFT,
    'П': Connection.BOTTOM_RIGHT,
    '0': Connection.BOTTOM_CENTER,
}

VARIANT_FIELDS = (
    'connection',
    'height_mm',
    'width_mm',
    'depth_mm',
    'axis_mm',
    'sections',
    'power_w',
    'orientation',
    'mount',
    'price',
    'currency',
    'is_active',
)

MISSING_COLUMNS = 'На листе «{}» нет колонок: {}'
UNKNOWN_SHEET = 'лист «{}» не знаком — добавьте в SHEETS: не импортирован'
UNKNOWN_MODEL = 'лист «{}»: модель «{}» не знакома — добавьте в FLOOR_MODELS'
NO_CONNECTION = 'лист «{}»: в артикуле «{}» нет кода подключения'
FOREIGN_SERIES = 'серия «{}» уже есть у другого бренда'
NO_PRICE = 'лист «{}»: без цены {} вариантов (в файле «{}»)'


@dataclass
class Row:
    sheet: Sheet
    article: str
    connection: str
    values: dict


@dataclass
class SeriesResult:
    series: Series
    created: bool
    variants: int = 0
    groups: list[str] = field(default_factory=list)


@dataclass
class Summary:
    series: list[SeriesResult] = field(default_factory=list)
    created: int = 0
    updated: int = 0
    hidden: int = 0
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def connection_of(article: str) -> tuple[str, int | None] | None:
    """Подключение и межосевое из кода в артикуле; None — кода нет.
    Межосевое бокового и нижнего по краям — из колонок N и E строки."""
    match = CONNECTION_CODE.search(article)
    if match is None:
        return None
    code = match.group(1)
    if code == 'БП':
        return Connection.SIDE, None
    if code == 'ЛП':
        return Connection.BOTTOM_ENDS, None
    return BOTTOM[code[0]], int(code[1:])


def _int(value) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return round(value) or None


def _price(value) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None  # «#REF!» и пустые — цена по запросу
    return Decimal(str(value)).quantize(KOPECK, rounding=ROUND_HALF_UP)


def parse_sheet(title: str, rows, summary: Summary) -> tuple[list[Row], bool]:
    """Строки листа → варианты; второе — можно ли любой RAL. Серия
    варианта — по листу, у напольных — по колонке «Модель»."""
    rows = iter(rows)
    notes = [str(c) for c in next(rows, ()) if isinstance(c, str)]
    header = [str(c).strip() if c is not None else '' for c in next(rows, ())]
    missing = [name for name in COLUMNS if name not in header]
    if missing:
        raise PriceFileError(MISSING_COLUMNS.format(title, ', '.join(missing)))
    column = {name: i for i, name in enumerate(header) if name}
    pairs = [
        i + 1
        for i, name in enumerate(header)
        if name == NAME and i + 1 < len(header) and header[i + 1] == ARTICLE
    ]
    result = []
    for cells in rows:
        cells = list(cells) + [None] * (len(header) - len(cells))
        row = {name: cells[i] for name, i in column.items()}
        sheet = _sheet_of(title, row, summary)
        if sheet is not None:
            articles = [cells[i] for i in pairs]
            result += _variants(title, sheet, row, articles, summary)
    no_price = sum(row.values['price'] is None for row in result)
    if no_price:
        summary.errors.append(NO_PRICE.format(title, no_price, TOTAL))
    any_ral = not any(ONLY_PAINT.search(note) for note in notes)
    return result, any_ral


def _sheet_of(title: str, row: dict, summary: Summary) -> Sheet | None:
    if title != FLOOR_SHEET:
        return SHEETS[title]
    model = ' '.join(str(row.get(MODEL) or '').split())
    sheet = FLOOR_MODELS.get(model)
    if sheet is None and model:
        summary.errors.append(UNKNOWN_MODEL.format(title, model))
    return sheet


def _variants(title, sheet: Sheet, row: dict, articles, summary) -> list[Row]:
    """Варианты строки — по одному на подключение с артикулом."""
    base = {
        'height_mm': _int(row.get(HEIGHT)),
        'width_mm': _int(row.get(LENGTH)),
        'depth_mm': _int(row.get(DEPTH)),
        'sections': _int(row.get(SECTIONS)),
        'power_w': _int(row.get(POWER)),
        'orientation': sheet.orientation,
        'mount': sheet.mount,
        'price': _price(row.get(TOTAL)),
        'currency': Currency.RUB,
        'is_active': True,
    }
    result = []
    for article in articles:
        if not isinstance(article, str) or not article.strip():
            continue
        article = ' '.join(article.split())
        parsed = connection_of(article)
        if parsed is None:
            summary.errors.append(NO_CONNECTION.format(title, article))
            continue
        connection, axis = parsed
        if axis is None:
            side = connection == Connection.SIDE
            axis = _int(row.get(AXIS_N if side else AXIS_E))
        values = {**base, 'connection': connection, 'axis_mm': axis}
        result.append(Row(sheet, article[:100], connection, values))
    return result


def import_velar(path, *, publish=False, dry_run=False) -> Summary:
    book = _open(path)
    summary = Summary()
    # серия → (строки, любой RAL у всех её листов)
    parsed: dict[str, tuple[list[Row], bool]] = {}
    active = active_split_parents()
    try:
        for title in book.sheetnames:
            if title in SKIPPED:
                summary.skipped.append(title)
                continue
            if title not in SHEETS and title != FLOOR_SHEET:
                summary.errors.append(UNKNOWN_SHEET.format(title))
                continue
            rows, any_ral = parse_sheet(
                title,
                book[title].iter_rows(values_only=True),
                summary,
            )
            for row in rows:
                row = route_velar(row, active)
                found, flag = parsed.get(row.sheet.slug, ([], True))
                found.append(row)
                parsed[row.sheet.slug] = (found, flag and any_ral)
    finally:
        book.close()
    if not parsed:
        return summary
    with muted_revalidation(), transaction.atomic():
        validate_split_parents({p for p in active if p.startswith('velar-')})
        _save(summary, parsed, publish=publish)
        if dry_run:
            transaction.set_rollback(True)
    if not dry_run:
        revalidate_frontend.delay(Tag.CATALOG)
    return summary


def _save(summary: Summary, parsed, *, publish: bool) -> None:
    brand, _ = Brand.objects.get_or_create(
        slug=BRAND_SLUG,
        defaults={'name': BRAND_NAME, 'is_published': False},
    )
    category, _ = Category.objects.get_or_create(
        slug=CATEGORY,
        defaults={'name': CATEGORY_NAME, 'is_published': False},
    )
    subcategory = Subcategory.objects.filter(
        slug=SUBCATEGORY,
        category=category,
    ).first()
    # Все варианты бренда: артикул уникален в бренде, и вариант, который
    # менеджер перенёс в другую серию, не должен создаться повторно
    existing = {
        (v.article, v.connection): v
        for v in Variant.objects.filter(brand=brand)
    }
    kept: set[tuple[str, str]] = set()
    imported = []
    for slug, (rows, any_ral) in parsed.items():
        name = rows[0].sheet.name
        series, created = Series.objects.get_or_create(
            slug=slug,
            defaults={
                'brand': brand,
                'category': category,
                'subcategory': subcategory,
                'name': name,
                'material': MATERIAL,
                'heating': Heating.WATER,
                'is_published': publish,
            },
        )
        if series.brand_id != brand.pk:
            summary.errors.append(FOREIGN_SERIES.format(slug))
            continue
        assign_family(series)
        imported.append(series.pk)
        result = SeriesResult(series, created)
        summary.series.append(result)
        _fill(series, subcategory, describe(slug, name, rows, any_ral=any_ral))
        result.groups = _groups(series, any_ral=any_ral)
        result.variants = len(rows)
        kept |= _save_variants(summary, series, rows, existing)
    hidden = [
        variant.pk
        for key, variant in existing.items()
        if key not in kept
        and variant.is_active
        and variant.series_id in imported
    ]
    Variant.objects.filter(pk__in=hidden).update(is_active=False)
    summary.hidden = len(hidden)
    recalculate(Variant.objects.filter(series_id__in=imported))


def _fill(series: Series, subcategory, description: str) -> None:
    """Пустые поля серии; заполненные — правка менеджера."""
    changed = []
    if not series.description.strip():
        series.description = description
        changed.append('description')
    if series.subcategory_id is None and subcategory is not None:
        series.subcategory = subcategory
        changed.append('subcategory')
    if not series.material:
        series.material = MATERIAL
        changed.append('material')
    if changed:
        series.save(update_fields=changed)


def _groups(series: Series, *, any_ral: bool) -> list[str]:
    """Группы цветов создаёт только первый импорт: белый RAL 9016 базовым,
    «Любой RAL» без доплаты — если лист не ограничивает покраску."""
    if series.color_groups.exists():
        return []
    white = Color.objects.filter(code=BASE_COLOR).first()
    base = ColorGroup.objects.create(
        series=series,
        name=BASE_GROUP,
        is_base=True,
        position=0,
    )
    if white is not None:
        base.colors.set([white])
    names = [BASE_GROUP]
    if any_ral:
        ColorGroup.objects.create(
            series=series,
            name=ANY_RAL_GROUP,
            any_ral=True,
            position=1,
        )
        names.append(ANY_RAL_GROUP)
    return names


def _save_variants(summary, series, rows: list[Row], existing) -> set:
    new, changed, kept = [], [], set()
    for row in rows:
        key = (row.article, row.connection)
        if key in kept:
            continue  # повтор строки в файле — первая главная
        kept.add(key)
        variant = existing.get(key)
        values = import_traits(series, row.values, variant)
        if variant is not None:
            if variant.series_id != series.pk:
                continue  # перенесён менеджером в другую серию
            if any(getattr(variant, k) != v for k, v in values.items()):
                for name, value in values.items():
                    setattr(variant, name, value)
                changed.append(variant)
            continue
        variant = Variant(
            series=series,
            brand_id=series.brand_id,
            article=row.article,
            **values,
        )
        existing[key] = variant
        new.append(variant)
    Variant.objects.bulk_create(new, batch_size=BATCH_SIZE)
    Variant.objects.bulk_update(changed, VARIANT_FIELDS, batch_size=BATCH_SIZE)
    summary.created += len(new)
    summary.updated += len(changed)
    return kept
