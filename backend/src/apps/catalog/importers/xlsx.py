"""Прайс Guardo и Nova — выгрузка заказчицы в xlsx.

Строка выгрузки — типоразмер в одном цвете. Строки одного артикула без
цвета сводятся в один вариант серии с ценой в базовом цвете, а цвета
раскладываются по группам серии с надбавкой (группы создаёт первый импорт,
дальше их правят менеджеры).
"""

import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.utils.text import slugify
from openpyxl import load_workbook

from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend

from ..choices import Connection, Currency, Finish, Heating, Mount, Orientation
from ..models import Brand, Category, Color, ColorGroup, Series, Variant
from ..pricing import recalculate

COLUMNS = (
    'Название',
    'Активность',
    'Длина, мм',
    'Высота, мм',
    'Ширина, мм',
    'Глубина, мм',
    'Цвет',
    'Межосевое, мм',
    'Мощность, Вт',
    'Тип нагрева',
    'Модель',
    'Бренд',
    'Артикул',
    'Розничная цена',
)
SHEETS = ('Guardo', 'Nova')

# Бренд в выгрузке → slug и название бренда на сайте
BRANDS = {
    'GUARDO': ('guardo', 'Guardo'),
    'Nova Radiators': ('nova', 'Nova'),
}
RADIATORS = 'radiatory'
TOWEL_RAILS = 'polotentsesushiteli'
CATEGORY_NAMES = {
    RADIATORS: 'Радиаторы',
    TOWEL_RAILS: 'Полотенцесушители',
}
TOWEL_RAIL_MODELS = frozenset(
    {'piatto', 'stretto', 'novanta', 'diagonale', 'alto', 'alto q'},
)
# Первая очередь: стекло Santarelli и арматура Multiflex+ не импортируются
SKIP_MODELS = ('santarelli', 'multiflex')

ANY_RAL = '*'
ANY_RAL_COLUMN = 'цвет ral'
CHROME = 'Хром'
GLOSS_SUFFIX = ' глянец'
BASE_COLOR = {'nova': 'RAL 9010'}
DEFAULT_BASE_COLOR = 'RAL 9016'
DEFAULT_HEX = '#cccccc'
RAL_HEX = {
    '1015': '#e6d2b5',
    '7012': '#575d5e',
    '7023': '#808076',
    '7024': '#474a50',
    '7040': '#9da3a6',
    '8019': '#3d3635',
    '8028': '#4e3b31',
    '9001': '#fdf4e3',
    '9005': '#0a0a0a',
    '9010': '#f7f5eb',
    '9016': '#f1f0ea',
}
# Цвет без кода RAL — по слову в названии
WORD_HEX = (
    ('технолак', '#8a8d8f'),
    ('хром', '#c0c4c8'),
    ('золот', '#c9a54a'),
    ('сталь', '#53565a'),
    ('бел', '#f1f0ea'),
    ('черн', '#0a0a0a'),
    ('чёрн', '#0a0a0a'),
)

BASE_GROUP = 'Стандартные'
ANY_RAL_GROUP = 'Любой RAL'
NEW_GROUP = 'Новые цвета'
# Новый цвет при повторном импорте идёт в группу с процентом ±1 п.
PERCENT_TOLERANCE = 1

NO_MODEL = '(без модели)'
MISSING_SHEET = 'В файле нет листа «{}», есть: {}'
MISSING_COLUMNS = 'На листе «{}» нет колонок: {}'

KOPECK = Decimal('0.01')
BATCH_SIZE = 1000

CONNECTION_RULES = (
    ('под электрику слева', Connection.ELECTRIC_LEFT, False),
    ('под электрику справа', Connection.ELECTRIC_RIGHT, False),
    ('нижнее центральное с вентилем', Connection.BOTTOM_CENTER, True),
    ('нижнее центральное', Connection.BOTTOM_CENTER, False),
    ('нижнее левое', Connection.BOTTOM_LEFT, False),
    ('нижнее правое', Connection.BOTTOM_RIGHT, False),
    ('нижнее по краям', Connection.BOTTOM_ENDS, False),
    ('нижнее в крайних секциях', Connection.BOTTOM_ENDS, False),
    ('нижнее с вентилем', Connection.BOTTOM_UNIVERSAL, True),
    ('нижнее', Connection.BOTTOM_UNIVERSAL, False),
    ('боковое', Connection.SIDE, False),
    ('диагональн', Connection.DIAGONAL, False),
)
CURRENCY_WORDS = (
    ('euro', Currency.EUR),
    ('eur', Currency.EUR),
    ('€', Currency.EUR),
    ('₽', Currency.RUB),
    ('руб', Currency.RUB),
    ('rub', Currency.RUB),
    ('usd', Currency.USD),
    ('$', Currency.USD),
    ('byn', Currency.BYN),
)
TUBE_WORDS = {
    'одно': 1,
    'двух': 2,
    'трех': 3,
    'четырех': 4,
    'пяти': 5,
    'шести': 6,
}

PRICE_NUMBER = re.compile(r'\d[\d\s.,]*')
# Pilon: «2T-0650 15 NKV» — трубность, высота, секции, подключение;
# дальше «3/4"», цвет словами и покраска — цвет берётся из колонки
PILON_ARTICLE = re.compile(r'^(\d)T-\d{4} (\d+) [A-Z]+')
NOVA_TUBES = re.compile(r'^NS-T(\d)')
COLOR_TOKEN = re.compile(
    r'(?<!\S)(?:'
    r'R(?P<ral>\d{4})\((?P<finish>[MGМ])\)'
    r'|(?P<any>RX{3,}|RALX*(?:\s+\((?:H-H|factory paint)\))?)'
    r'|(?P<chrome>CH)'
    r')(?!\S)',
)
TUBES_IN_NAME = re.compile(
    r'(одно|двух|тр[её]х|четыр[её]х|пяти|шести)трубн',
    re.IGNORECASE,
)
SECTIONS_IN_NAME = re.compile(r'(\d+)\s+(?:секци|перекладин)', re.IGNORECASE)
HORIZONTAL = re.compile(r'\bGOR\b')
VERTICAL = re.compile(r'\bVER\b')
FLOOR = re.compile(r'-FL\b')
BK_CODE = re.compile(r'\bBK\b')
DIGITS = re.compile(r'\d+')

VARIANT_FIELDS = (
    'height_mm',
    'width_mm',
    'depth_mm',
    'length_mm',
    'axis_mm',
    'sections',
    'power_w',
    'tubes',
    'connection',
    'thermovalve',
    'orientation',
    'mount',
    'price',
    'currency',
    'is_active',
    'attrs',
)


class PriceFileError(Exception):
    """Файл не похож на выгрузку: нет листа или колонок."""


@dataclass(slots=True)
class ParsedRow:
    brand_slug: str
    brand_name: str
    series_name: str
    series_slug: str
    category_slug: str
    base_article: str
    color_name: str
    color_code: str
    finish: str
    length_mm: int | None
    height_mm: int | None
    width_mm: int | None
    depth_mm: int | None
    axis_mm: int | None
    power_w: int | None
    tubes: int | None
    sections: int | None
    orientation: str
    mount: str
    connection: str
    thermovalve: bool
    heating: str
    price: Decimal | None
    currency: str
    is_active: bool


# --- разбор строки ---


def parse_price(text) -> tuple[Decimal, str] | None:
    """«1.613,98 euro», «5 480.00 ₽», «1.001.49 ₽» → (число, валюта).

    Запятая — дробная часть; без запятой все точки, кроме последней, —
    разделители тысяч.
    """
    text = str(text or '').strip()
    match = PRICE_NUMBER.search(text)
    lowered = text.lower()
    currency = next(
        (code for word, code in CURRENCY_WORDS if word in lowered),
        None,
    )
    if match is None or currency is None:
        return None
    number = re.sub(r'\s', '', match.group()).rstrip('.,')
    if ',' in number:
        number = number.replace('.', '').replace(',', '.')
    else:
        whole, dot, fraction = number.rpartition('.')
        number = whole.replace('.', '') + dot + fraction
    try:
        return Decimal(number), currency
    except InvalidOperation:
        return None


def parse_connection(name: str) -> tuple[str, bool]:
    """Подключение и термоклапан — по словам названия: коды в артикуле
    неоднозначны (у Retta «BK-GOR» и боковое, и нижнее по краям)."""
    lowered = (name or '').lower()
    for words, connection, thermovalve in CONNECTION_RULES:
        if words in lowered:
            return str(connection), thermovalve
    return '', False


def _text(value) -> str:
    return str(value).strip() if value is not None else ''


def _number(value) -> int | None:
    if isinstance(value, int | float):
        number = round(value)
    else:
        digits = DIGITS.search(_text(value))
        number = int(digits.group()) if digits else 0
    return number if number > 0 else None


def _finish(name: str) -> str:
    lowered = name.lower()
    if 'матов' in lowered:
        return Finish.MATTE
    if 'глян' in lowered:
        return Finish.GLOSS
    return ''


def _series(model: str, brand_name: str) -> tuple[str, str]:
    """«GUARDO RETTA 3P» → «Guardo Retta 3P», «PIATTO» → «Guardo Piatto»."""
    words = model.split()
    if words[0].lower() == brand_name.lower():
        words = words[1:]
    words = [
        word.capitalize() if word.isalpha() and len(word) > 1 else word.upper()
        for word in words
    ]
    return ' '.join([brand_name, *words]), ' '.join(words).lower()


def _color(article: str, column: str) -> tuple[str, str, str, str]:
    """Артикул без цвета, код цвета, название и покрытие."""
    pilon = PILON_ARTICLE.match(article)
    if pilon:
        return pilon.group(), column, column, _finish(column)
    token = COLOR_TOKEN.search(article)
    if token:
        base = article[: token.start()] + article[token.end() :]
    elif column and column.lower() in article.lower():
        start = article.lower().index(column.lower())
        base = article[:start] + article[start + len(column) :]
    else:
        base = article
    base = ' '.join(base.split())
    if token and token['ral']:
        gloss = token['finish'] == 'G'
        code = f'RAL {token["ral"]}' + (GLOSS_SUFFIX if gloss else '')
        finish = Finish.GLOSS if gloss else Finish.MATTE
        return base, code, column or code, finish
    if (token and token['any']) or column.lower() == ANY_RAL_COLUMN:
        return base, ANY_RAL, column, ''
    if token and token['chrome']:
        return base, CHROME, column or CHROME, ''
    return base, column, column, _finish(column)


def _heating(value: str) -> str:
    lowered = value.lower()
    if 'электр' in lowered:
        return Heating.ELECTRIC
    if 'водян' in lowered:
        return Heating.WATER
    return ''


def parse_row(row: dict) -> ParsedRow | None:
    """Строка выгрузки → поля варианта; None — строку не импортируем."""
    model = _text(row.get('Модель'))
    article = ' '.join(_text(row.get('Артикул')).split())
    brand = BRANDS.get(_text(row.get('Бренд')))
    if (
        not model
        or not article
        or brand is None
        or model.lower().startswith(SKIP_MODELS)
    ):
        return None
    brand_slug, brand_name = brand
    name = _text(row.get('Название'))
    series_name, model_key = _series(model, brand_name)
    base, code, color_name, finish = _color(article, _text(row.get('Цвет')))

    # Трубность и секции — из названия, у Pilon и Nova есть и в артикуле
    pilon = PILON_ARTICLE.match(article)
    in_article = pilon or NOVA_TUBES.match(article)
    tubes_word = TUBES_IN_NAME.search(name)
    sections_word = SECTIONS_IN_NAME.search(name)
    tubes = sections = None
    if tubes_word:
        tubes = TUBE_WORDS[tubes_word.group(1).lower().replace('ё', 'е')]
    elif in_article:
        tubes = int(in_article.group(1))
    if sections_word:
        sections = int(sections_word.group(1))
    elif pilon:
        sections = int(pilon.group(2))

    if HORIZONTAL.search(article):
        orientation = Orientation.HORIZONTAL
    elif VERTICAL.search(article) or 'вертикальн' in name.lower():
        orientation = Orientation.VERTICAL
    else:
        orientation = ''
    connection, thermovalve = parse_connection(name)
    price = parse_price(row.get('Розничная цена'))
    return ParsedRow(
        brand_slug=brand_slug,
        brand_name=brand_name,
        series_name=series_name,
        series_slug=slugify(series_name),
        category_slug=(
            TOWEL_RAILS if model_key in TOWEL_RAIL_MODELS else RADIATORS
        ),
        base_article=base,
        color_name=color_name,
        color_code=code,
        finish=finish,
        length_mm=_number(row.get('Длина, мм')),
        height_mm=_number(row.get('Высота, мм')),
        width_mm=_number(row.get('Ширина, мм')),
        depth_mm=_number(row.get('Глубина, мм')),
        axis_mm=_number(row.get('Межосевое, мм')),
        power_w=_number(row.get('Мощность, Вт')),
        tubes=tubes,
        sections=sections,
        orientation=str(orientation),
        mount=Mount.FLOOR if FLOOR.search(article) else '',
        connection=connection,
        thermovalve=thermovalve,
        heating=_heating(_text(row.get('Тип нагрева'))),
        price=price[0] if price else None,
        currency=price[1] if price else Currency.BYN,
        is_active=_text(row.get('Активность')) == 'Да',
    )


# --- импорт ---


@dataclass
class Summary:
    sheet: str
    rows: int = 0
    skipped: Counter = field(default_factory=Counter)
    duplicates: int = 0
    # артикул → сколько строк с другими размерами или подключением
    conflicts: Counter = field(default_factory=Counter)
    series_new: list = field(default_factory=list)
    series_total: int = 0
    created: int = 0
    updated: int = 0
    hidden: int = 0


def read_rows(sheet):
    rows = sheet.iter_rows(values_only=True)
    header = [_text(cell) for cell in next(rows, ())]
    missing = [column for column in COLUMNS if column not in header]
    if missing:
        raise PriceFileError(
            MISSING_COLUMNS.format(sheet.title, ', '.join(missing)),
        )
    for values in rows:
        if any(value is not None for value in values):
            yield dict(zip(header, values, strict=False))


def import_file(path, sheets=None, *, dry_run=False) -> list[Summary]:
    """Импорт листов, каждый — одной транзакцией; сброс кэша фронта —
    один раз в конце. sheets=None — те из Guardo и Nova, что есть в файле;
    dry_run — всё посчитать и откатить."""
    book = load_workbook(path, read_only=True, data_only=True)
    try:
        if sheets is None:
            sheets = [name for name in SHEETS if name in book.sheetnames]
        for name in sheets or SHEETS:
            if name not in book.sheetnames:
                raise PriceFileError(
                    MISSING_SHEET.format(name, ', '.join(book.sheetnames)),
                )
        summaries = []
        with muted_revalidation():
            for name in sheets:
                with transaction.atomic():
                    summaries.append(import_rows(name, read_rows(book[name])))
                    if dry_run:
                        transaction.set_rollback(True)
    finally:
        book.close()
    if not dry_run:
        revalidate_frontend.delay(Tag.CATALOG)
    return summaries


def _group_rows(summary: Summary, rows):
    """Строки → серия → артикул → код цвета → строка."""
    grouped = defaultdict(dict)
    article_series = {}
    for row in rows:
        summary.rows += 1
        parsed = parse_row(row)
        if parsed is None:
            summary.skipped[_text(row.get('Модель')) or NO_MODEL] += 1
            continue
        key = (parsed.brand_slug, parsed.base_article)
        if article_series.setdefault(key, parsed.series_slug) != (
            parsed.series_slug
        ):
            summary.duplicates += 1
            continue
        colors = grouped[parsed.series_slug].setdefault(
            parsed.base_article,
            {},
        )
        kept = colors.get(parsed.color_code)
        if kept is not None:
            if _same_variant(kept, parsed):
                summary.duplicates += 1
            else:
                summary.conflicts[parsed.base_article] += 1
            if not _prefer(parsed, kept):
                continue
        colors[parsed.color_code] = parsed
    return grouped, article_series


def import_rows(sheet: str, rows) -> Summary:
    summary = Summary(sheet)
    grouped, article_series = _group_rows(summary, rows)

    brands, variants = {}, {}
    for slug, bases in grouped.items():
        first = next(iter(next(iter(bases.values())).values()))
        if first.brand_slug not in brands:
            brand = _brand(first)
            brands[first.brand_slug] = brand
            variants[first.brand_slug] = {
                variant.article: variant
                for variant in Variant.objects.filter(brand=brand)
            }
        series, created = Series.objects.get_or_create(
            slug=slug,
            defaults={
                'brand': brands[first.brand_slug],
                'category': _category(first.category_slug),
                'name': first.series_name,
                'is_published': False,
                'heating': _series_heating(bases),
            },
        )
        if created:
            summary.series_new.append(series)
        groups = _update_groups(series, bases, first.brand_slug)
        _save_variants(
            summary,
            series,
            bases,
            groups,
            variants[first.brand_slug],
        )
    summary.series_total = len(grouped)

    # Пропавшие из файла варианты бренда скрываются с сайта
    for (brand_slug, article), _ in article_series.items():
        variants[brand_slug].pop(article, None)
    hidden = [
        variant.pk
        for existing in variants.values()
        for variant in existing.values()
        if variant.is_active
    ]
    Variant.objects.filter(pk__in=hidden).update(is_active=False)
    summary.hidden = len(hidden)
    if brands:
        recalculate(Variant.objects.filter(brand__in=brands.values()))
    return summary


def _same_variant(kept: ParsedRow, parsed: ParsedRow) -> bool:
    return (kept.height_mm, kept.width_mm, kept.connection) == (
        parsed.height_mm,
        parsed.width_mm,
        parsed.connection,
    )


def _prefer(parsed: ParsedRow, kept: ParsedRow) -> bool:
    """Один артикул Retta / Torre в выгрузке дважды: стоя с боковым
    подключением и повёрнутый, с нижним по краям. Ключ — артикул, поэтому
    остаётся одна строка — та, что совпадает с кодом «BK» (боковое), чтобы
    выбор не зависел от порядка строк в файле."""
    return (
        BK_CODE.search(parsed.base_article) is not None
        and parsed.connection == Connection.SIDE
        and kept.connection != Connection.SIDE
    )


def _brand(parsed: ParsedRow) -> Brand:
    # Новый бренд или категорию менеджер заполняет и публикует в админке
    brand, _ = Brand.objects.get_or_create(
        slug=parsed.brand_slug,
        defaults={'name': parsed.brand_name, 'is_published': False},
    )
    return brand


def _category(slug: str) -> Category:
    category, _ = Category.objects.get_or_create(
        slug=slug,
        defaults={'name': CATEGORY_NAMES[slug], 'is_published': False},
    )
    return category


def _series_heating(bases) -> str:
    heating = {
        parsed.heating
        for colors in bases.values()
        for parsed in colors.values()
    }
    if heating == {Heating.ELECTRIC}:
        return Heating.ELECTRIC
    return Heating.WATER


def _colors(bases) -> dict[str, Color]:
    """Палитра: недостающие цвета создаются, существующие не меняются."""
    wanted = {}
    for colors in bases.values():
        for code, parsed in colors.items():
            if code and code != ANY_RAL:
                wanted.setdefault(code, parsed)
    found = {c.code: c for c in Color.objects.filter(code__in=wanted)}
    Color.objects.bulk_create(
        [
            Color(
                code=code,
                name=parsed.color_name[:100],
                hex=_hex(code, parsed.color_name),
                finish=parsed.finish,
            )
            for code, parsed in wanted.items()
            if code not in found
        ],
        ignore_conflicts=True,
    )
    return {c.code: c for c in Color.objects.filter(code__in=wanted)}


def _hex(code: str, name: str) -> str:
    ral = code.removeprefix('RAL ').split()[0]
    if ral in RAL_HEX:
        return RAL_HEX[ral]
    lowered = name.lower()
    return next(
        (value for word, value in WORD_HEX if word in lowered),
        DEFAULT_HEX,
    )


def _reference(colors, known) -> tuple[Decimal, str, str] | None:
    """Цена варианта в базовом цвете: из цвета базовой группы, а если его
    у варианта нет — из цвета с наименьшей надбавкой (минус надбавка)."""
    priced = [
        (known[code] != 0, known[code], index, code, parsed)
        for index, (code, parsed) in enumerate(colors.items())
        if code in known and parsed.price is not None
    ]
    if not priced:
        return None
    _, percent, _, code, parsed = min(priced, key=lambda item: item[:3])
    price = parsed.price / (1 + Decimal(percent) / 100)
    return (
        price.quantize(KOPECK, rounding=ROUND_HALF_UP),
        parsed.currency,
        code,
    )


def _percents(bases, known) -> dict[str, int | None]:
    """Надбавка новых цветов к базовому: медиана отношений по вариантам,
    до целого процента; None — не с чем сравнить."""
    ratios = defaultdict(list)
    found = {}
    for colors in bases.values():
        reference = _reference(colors, known)
        for code, parsed in colors.items():
            if code in known or code in {ANY_RAL, ''}:
                continue
            found.setdefault(code, None)
            if (
                reference is None
                or parsed.price is None
                or parsed.currency != reference[1]
            ):
                continue
            ratios[code].append(parsed.price / reference[0])
    for code, values in ratios.items():
        percent = (statistics.median(values) - 1) * 100
        found[code] = int(percent.quantize(Decimal(1), ROUND_HALF_UP))
    return found


def _base_code(bases, brand_slug: str) -> str | None:
    counts = Counter(
        code
        for colors in bases.values()
        for code in colors
        if code not in {ANY_RAL, ''}
    )
    preferred = BASE_COLOR.get(brand_slug, DEFAULT_BASE_COLOR)
    if preferred in counts:
        return preferred
    return counts.most_common(1)[0][0] if counts else None


def _group_name(color: Color, percent: int) -> str:
    sign = '+' if percent > 0 else '−'
    return f'{color.name} {sign}{abs(percent)} %'


def _update_groups(series, bases, brand_slug) -> list[ColorGroup]:
    """Первый импорт серии (у неё ещё нет групп) раскладывает цвета по
    надбавке; повторный только добавляет новые цвета, проценты не трогает."""
    palette = _colors(bases)
    groups = list(series.color_groups.prefetch_related('colors'))
    has_any_ral = any(ANY_RAL in colors for colors in bases.values())
    if not groups:
        base_code = _base_code(bases, brand_slug)
        known = {base_code: 0} if base_code else {}
        by_percent = defaultdict(list)
        for code, percent in _percents(bases, known).items():
            by_percent[percent or 0].append(code)
        base = ColorGroup.objects.create(
            series=series,
            name=BASE_GROUP,
            is_base=True,
        )
        base.colors.set(
            [palette[code] for code in [*known, *by_percent.pop(0, [])]],
        )
        groups = [base]
        for position, percent in enumerate(sorted(by_percent), start=1):
            codes = by_percent[percent]
            group = ColorGroup.objects.create(
                series=series,
                name=_group_name(palette[codes[0]], percent),
                percent=percent,
                position=position,
            )
            group.colors.set([palette[code] for code in codes])
            groups.append(group)
        if has_any_ral:
            groups.append(_any_ral_group(series, len(groups)))
        return groups

    known = {
        color.code: group.percent
        for group in groups
        for color in group.colors.all()
    }
    priced = [group for group in groups if not group.any_ral]
    for code, percent in _percents(bases, known).items():
        close = [
            group
            for group in priced
            if percent is not None
            and abs(group.percent - percent) <= PERCENT_TOLERANCE
        ]
        if close:
            group = min(close, key=lambda g: abs(g.percent - percent))
        else:
            group = next((g for g in groups if g.name == NEW_GROUP), None)
            if group is None:
                group = ColorGroup.objects.create(
                    series=series,
                    name=NEW_GROUP,
                    percent=percent or 0,
                    position=max(g.position for g in groups) + 1,
                )
                groups.append(group)
                priced.append(group)
        group.colors.add(palette[code])
    if has_any_ral and not any(group.any_ral for group in groups):
        position = max(g.position for g in groups) + 1
        groups.append(_any_ral_group(series, position))
    return list(series.color_groups.prefetch_related('colors'))


def _any_ral_group(series, position) -> ColorGroup:
    return ColorGroup.objects.create(
        series=series,
        name=ANY_RAL_GROUP,
        any_ral=True,
        position=position,
    )


def _values(parsed: ParsedRow, price: Decimal | None, is_active: bool):
    return {
        'height_mm': parsed.height_mm,
        'width_mm': parsed.width_mm,
        'depth_mm': parsed.depth_mm,
        'length_mm': parsed.length_mm,
        'axis_mm': parsed.axis_mm,
        'sections': parsed.sections,
        'power_w': parsed.power_w,
        'tubes': parsed.tubes,
        'connection': parsed.connection,
        'thermovalve': parsed.thermovalve,
        'orientation': parsed.orientation,
        'mount': parsed.mount,
        'price': price,
        'currency': parsed.currency,
        'is_active': is_active,
    }


def _save_variants(summary, series, bases, groups, existing):
    known = {
        color.code: group.percent
        for group in groups
        for color in group.colors.all()
    }
    group_of = {
        color.code: group.pk
        for group in groups
        for color in group.colors.all()
    }
    any_ral = next((group.pk for group in groups if group.any_ral), None)
    all_groups = {group.pk for group in groups}
    towel_rail = series.category.slug == TOWEL_RAILS

    new, changed, availability = [], [], {}
    for article, colors in bases.items():
        reference = _reference(colors, known)
        if reference:
            price, _, code = reference
            parsed = colors[code]
        else:
            price, parsed = None, next(iter(colors.values()))
        values = _values(
            parsed,
            price,
            any(row.is_active for row in colors.values()),
        )
        variant = existing.get(article)
        attrs = dict(variant.attrs) if variant else {}
        if towel_rail and parsed.heating:
            attrs['heating'] = parsed.heating
        values['attrs'] = attrs
        if variant is None:
            variant = Variant(
                series=series,
                brand_id=series.brand_id,
                article=article,
                **values,
            )
            new.append(variant)
        elif any(getattr(variant, k) != v for k, v in values.items()):
            for name, value in values.items():
                setattr(variant, name, value)
            changed.append(variant)
        available = {group_of[code] for code in colors if code in group_of}
        if ANY_RAL in colors and any_ral:
            available.add(any_ral)
        availability[article] = available if available != all_groups else ()

    Variant.objects.bulk_create(new, batch_size=BATCH_SIZE)
    Variant.objects.bulk_update(changed, VARIANT_FIELDS, batch_size=BATCH_SIZE)
    summary.created += len(new)
    summary.updated += len(changed)
    for variant in new:
        existing[variant.article] = variant

    through = Variant.color_groups.through
    ids = [existing[article].pk for article in bases]
    for start in range(0, len(ids), BATCH_SIZE):
        through.objects.filter(
            variant_id__in=ids[start : start + BATCH_SIZE],
        ).delete()
    through.objects.bulk_create(
        [
            through(variant_id=existing[article].pk, colorgroup_id=group)
            for article, available in availability.items()
            for group in available
        ],
        batch_size=BATCH_SIZE * 5,
    )
