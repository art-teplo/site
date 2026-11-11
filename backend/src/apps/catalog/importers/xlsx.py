"""Импорт прайса Guardo и Nova — выгрузки заказчицы в xlsx.

Строка выгрузки — типоразмер в одном цвете. Строки одного артикула без
цвета сводятся в один вариант серии с ценой в базовом цвете. Группы цветов
с надбавкой создаёт только первый импорт серии; дальше их ведут менеджеры,
а импорт лишь сообщает о цветах, которых нет в группах.
"""

import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from zipfile import BadZipFile

from django.db import transaction
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend

from ..choices import Connection, Heating
from ..models import Brand, Category, Color, ColorGroup, Series, Variant
from ..pricing import recalculate
from .parse import (
    ANY_RAL,
    BK_CODE,
    COLUMNS,
    TOWEL_RAILS,
    ParsedRow,
    clean_text,
    parse_row,
)

SHEETS = ('Guardo', 'Nova')
CATEGORY_NAMES = {
    'radiatory': 'Радиаторы',
    TOWEL_RAILS: 'Полотенцесушители',
}
BASE_COLOR = {'nova': 'RAL 9010'}
DEFAULT_BASE_COLOR = 'RAL 9016'

# Цвет попадает в группу на первом импорте, только если он есть хотя бы у
# 5 % артикулов серии (не меньше трёх, но не больше, чем артикулов в серии)
# и не дешевле базового: иначе это, скорее всего, ошибка прайса.
MIN_SUPPORT_SHARE = Decimal('0.05')
MIN_SUPPORT = 3

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
NO_MODEL = '(без модели)'
MISSING_SHEET = 'В файле нет листа «{}», есть: {}'
MISSING_COLUMNS = 'На листе «{}» нет колонок: {}'
NOT_FOUND = 'Нет файла {}'
NOT_XLSX = 'Не удалось прочитать {} как xlsx — это точно выгрузка Excel?'
FOREIGN_SERIES = 'серия «{}» уже есть у другого бренда'

KOPECK = Decimal('0.01')
BATCH_SIZE = 1000

NUMBER_FIELDS = (
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
    'currency',
)
VARIANT_FIELDS = (*NUMBER_FIELDS, 'price', 'is_active', 'attrs')


class PriceFileError(Exception):
    """Файл не похож на выгрузку: не открывается, нет листа или колонок."""


@dataclass
class SeriesReport:
    series: Series
    created: bool
    # Создано первым импортом: название, процент, у скольких артикулов
    groups: list = field(default_factory=list)
    # Не попали в группы на первом импорте: цвет, процент, артикулов
    skipped: list = field(default_factory=list)
    # Повторный импорт: цвета из файла, которых нет в группах серии
    ungrouped: list = field(default_factory=list)


@dataclass
class Summary:
    sheet: str
    rows: int = 0
    skipped: Counter = field(default_factory=Counter)
    duplicates: int = 0
    # артикул → сколько строк с другими размерами или подключением
    conflicts: Counter = field(default_factory=Counter)
    series: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    created: int = 0
    updated: int = 0
    hidden: int = 0

    @property
    def series_new(self) -> list[Series]:
        return [report.series for report in self.series if report.created]


def color_label(code: str, name: str = '') -> str:
    if code == ANY_RAL:
        return ANY_RAL_GROUP
    return f'{name} ({code})' if name and name != code else code


def read_rows(sheet):
    rows = sheet.iter_rows(values_only=True)
    header = [clean_text(cell) for cell in next(rows, ())]
    missing = [column for column in COLUMNS if column not in header]
    if missing:
        raise PriceFileError(
            MISSING_COLUMNS.format(sheet.title, ', '.join(missing)),
        )
    for values in rows:
        if any(value is not None for value in values):
            yield dict(zip(header, values, strict=False))


def _open(path):
    try:
        return load_workbook(path, read_only=True, data_only=True)
    except FileNotFoundError as error:
        raise PriceFileError(NOT_FOUND.format(path)) from error
    except (BadZipFile, InvalidFileException, KeyError, OSError) as error:
        raise PriceFileError(NOT_XLSX.format(path)) from error


def import_file(path, sheets=None, *, dry_run=False) -> list[Summary]:
    """Импорт листов, каждый — одной транзакцией; сброс кэша фронта —
    один раз в конце. sheets=None — те из Guardo и Nova, что есть в файле;
    dry_run — всё посчитать и откатить."""
    book = _open(path)
    summaries = []
    try:
        if sheets is None:
            sheets = [name for name in SHEETS if name in book.sheetnames]
        for name in sheets or SHEETS:
            if name not in book.sheetnames:
                raise PriceFileError(
                    MISSING_SHEET.format(name, ', '.join(book.sheetnames)),
                )
        with muted_revalidation():
            for name in sheets:
                with transaction.atomic():
                    summaries.append(import_rows(name, read_rows(book[name])))
                    if dry_run:
                        transaction.set_rollback(True)
    finally:
        book.close()
        # Сохранённые листы сбрасывают кэш, даже если следующий упал
        if summaries and not dry_run:
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
            summary.skipped[clean_text(row.get('Модель')) or NO_MODEL] += 1
            continue
        key = (parsed.brand_slug, parsed.base_article)
        if article_series.setdefault(key, parsed.series_slug) != (
            parsed.series_slug
        ):
            summary.conflicts[parsed.base_article] += 1
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


def _first(bases) -> ParsedRow:
    return next(iter(next(iter(bases.values())).values()))


def import_rows(sheet: str, rows) -> Summary:
    summary = Summary(sheet)
    grouped, article_series = _group_rows(summary, rows)

    brands, variants = {}, {}
    for slug, bases in grouped.items():
        first = _first(bases)
        if first.brand_slug not in brands:
            brand = _brand(first)
            brands[first.brand_slug] = brand
            variants[first.brand_slug] = {
                variant.article: variant
                for variant in Variant.objects.filter(brand=brand)
            }
        brand = brands[first.brand_slug]
        series, created = Series.objects.get_or_create(
            slug=slug,
            defaults={
                'brand': brand,
                'category': _category(first.category_slug),
                'name': first.series_name,
                'is_published': False,
                'heating': _series_heating(bases),
            },
        )
        if series.brand_id != brand.pk:
            summary.errors.append(FOREIGN_SERIES.format(slug))
            continue
        report = SeriesReport(series, created)
        summary.series.append(report)
        groups = _update_groups(report, bases, first.brand_slug)
        _save_variants(
            summary,
            series,
            bases,
            groups,
            variants[first.brand_slug],
        )

    # Пропавшие из файла варианты бренда скрываются с сайта
    for brand_slug, article in article_series:
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


def _hex(code: str, name: str) -> str:
    ral = code.removeprefix('RAL ').split()[0]
    if ral in RAL_HEX:
        return RAL_HEX[ral]
    lowered = name.lower()
    return next(
        (value for word, value in WORD_HEX if word in lowered),
        DEFAULT_HEX,
    )


def _palette(rows: dict[str, ParsedRow]) -> dict[str, Color]:
    """Цвета групп: недостающие создаются, существующие не меняются."""
    found = {c.code: c for c in Color.objects.filter(code__in=rows)}
    Color.objects.bulk_create(
        [
            Color(
                code=code,
                name=parsed.color_name[:100],
                hex=_hex(code, parsed.color_name),
                finish=parsed.finish,
            )
            for code, parsed in rows.items()
            if code not in found
        ],
        ignore_conflicts=True,
    )
    return {c.code: c for c in Color.objects.filter(code__in=rows)}


def _reference(
    colors,
    known,
    preferred: str,
) -> tuple[Decimal, str, str] | None:
    """Цена варианта в базовом цвете: из цвета базовой группы (сначала
    белый бренда, дальше по коду — не по порядку строк в файле), а если
    его у варианта нет — из цвета с наименьшей надбавкой (минус надбавка)."""
    priced = [
        (known[code] != 0, known[code], code != preferred, code, parsed)
        for code, parsed in colors.items()
        if code in known and parsed.price is not None
    ]
    if not priced:
        return None
    *_, code, parsed = min(priced, key=lambda item: item[:4])
    percent = known[code]
    price = parsed.price / (1 + Decimal(percent) / 100)
    return (
        price.quantize(KOPECK, rounding=ROUND_HALF_UP),
        parsed.currency,
        code,
    )


def _percents(bases, base_code: str) -> dict[str, int | None]:
    """Надбавка цветов к базовому: медиана отношений по вариантам, до
    целого процента; None — не с чем сравнить (нет базового цвета или
    другая валюта)."""
    ratios = defaultdict(list)
    found = {}
    for colors in bases.values():
        base = colors.get(base_code)
        for code, parsed in colors.items():
            if code in {base_code, ANY_RAL, ''}:
                continue
            found.setdefault(code, None)
            if (
                base is None
                or base.price is None
                or parsed.price is None
                or parsed.currency != base.currency
            ):
                continue
            ratios[code].append(parsed.price / base.price)
    for code, values in ratios.items():
        percent = (statistics.median(values) - 1) * 100
        found[code] = int(percent.quantize(Decimal(1), ROUND_HALF_UP))
    return found


def _base_code(support: Counter, brand_slug: str) -> str | None:
    preferred = BASE_COLOR.get(brand_slug, DEFAULT_BASE_COLOR)
    if preferred in support:
        return preferred
    real = [(n, code) for code, n in support.items() if code != ANY_RAL]
    return max(real, key=lambda item: item[0])[1] if real else None


def _group_name(name: str, percent: int) -> str:
    return f'{name} +{percent} %'


def _update_groups(report: SeriesReport, bases, brand_slug):
    """Группы создаёт только первый импорт (у серии ещё нет групп).
    Если группы есть, импорт их не трогает — только перечисляет цвета
    файла, которых в группах нет."""
    series = report.series
    support = Counter(code for colors in bases.values() for code in colors)
    support.pop('', None)
    rows = {}
    for colors in bases.values():
        for code, parsed in colors.items():
            rows.setdefault(code, parsed)
    groups = list(series.color_groups.prefetch_related('colors'))
    if groups:
        grouped = {c.code for group in groups for c in group.colors.all()}
        if any(group.any_ral for group in groups):
            grouped.add(ANY_RAL)
        report.ungrouped = [
            color_label(code, rows[code].color_name)
            for code in support
            if code not in grouped
        ]
        return groups

    threshold = min(
        len(bases),
        max(MIN_SUPPORT, math.ceil(len(bases) * MIN_SUPPORT_SHARE)),
    )
    base_code = _base_code(support, brand_slug)
    by_percent = defaultdict(list)
    for code, percent in _percents(bases, base_code).items():
        if support[code] >= threshold and (percent or 0) >= 0:
            by_percent[percent or 0].append(code)
        else:
            report.skipped.append(
                (
                    color_label(code, rows[code].color_name),
                    percent,
                    support[code],
                ),
            )
    if ANY_RAL in support and support[ANY_RAL] < threshold:
        report.skipped.append((ANY_RAL_GROUP, None, support[ANY_RAL]))
        support.pop(ANY_RAL)

    base_codes = [base_code] if base_code else []
    plan = [(BASE_GROUP, 0, [*base_codes, *by_percent.pop(0, [])])]
    plan += [
        (_group_name(rows[codes[0]].color_name, percent), percent, codes)
        for percent, codes in sorted(by_percent.items())
    ]
    palette = _palette(
        {code: rows[code] for _, _, codes in plan for code in codes}
    )
    groups = []
    for position, (name, percent, codes) in enumerate(plan):
        group = ColorGroup.objects.create(
            series=series,
            name=name,
            percent=percent,
            is_base=position == 0,
            position=position,
        )
        group.colors.set([palette[code] for code in codes])
        groups.append(group)
        report.groups.append((name, percent, _support(bases, codes)))
    if ANY_RAL in support:
        groups.append(
            ColorGroup.objects.create(
                series=series,
                name=ANY_RAL_GROUP,
                any_ral=True,
                position=len(groups),
            ),
        )
        report.groups.append((ANY_RAL_GROUP, None, support[ANY_RAL]))
    return groups


def _support(bases, codes) -> int:
    codes = set(codes)
    return sum(1 for colors in bases.values() if codes & colors.keys())


def _save_variants(summary, series, bases, groups, existing):
    preferred = BASE_COLOR.get(series.brand.slug, DEFAULT_BASE_COLOR)
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
    if any_ral:
        group_of[ANY_RAL] = any_ral
    # «Все группы» — те, чьи цвета есть в файле: группа, которую менеджер
    # завёл сам, не делает каждый вариант «частичным»
    in_file = {
        group_of[c]
        for colors in bases.values()
        for c in colors
        if c in group_of
    }
    towel_rail = series.category.slug == TOWEL_RAILS

    new, changed, availability = [], [], {}
    for article, colors in bases.items():
        reference = _reference(colors, known, preferred)
        if reference:
            price, _, code = reference
            parsed = colors[code]
        else:
            price, parsed = None, next(iter(colors.values()))
        values = {name: getattr(parsed, name) for name in NUMBER_FIELDS}
        values['price'] = price
        values['is_active'] = any(row.is_active for row in colors.values())
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
        availability[article] = available if available != in_file else set()

    Variant.objects.bulk_create(new, batch_size=BATCH_SIZE)
    Variant.objects.bulk_update(changed, VARIANT_FIELDS, batch_size=BATCH_SIZE)
    summary.created += len(new)
    summary.updated += len(changed)
    for variant in new:
        existing[variant.article] = variant
    _save_availability(series, existing, availability)


def _save_availability(series, existing, availability):
    """Связи вариант — группа переписываются только у вариантов, где набор
    поменялся. Вариант, который менеджер перенёс в другую серию, не трогаем:
    группы у него чужие."""
    through = Variant.color_groups.through
    current = defaultdict(set)
    for variant_id, group_id in through.objects.filter(
        variant__series=series,
    ).values_list('variant_id', 'colorgroup_id'):
        current[variant_id].add(group_id)
    stale, links = [], []
    for article, wanted in availability.items():
        variant = existing[article]
        if variant.series_id != series.pk or current[variant.pk] == wanted:
            continue
        stale.append(variant.pk)
        links += [
            through(variant_id=variant.pk, colorgroup_id=group)
            for group in wanted
        ]
    for start in range(0, len(stale), BATCH_SIZE):
        through.objects.filter(
            variant_id__in=stale[start : start + BATCH_SIZE],
        ).delete()
    through.objects.bulk_create(links, batch_size=BATCH_SIZE * 5)
