"""Разбор параметров списка, фильтрация вариантов и счётчики фасетов.

Разобранные параметры самодостаточны (источник и делитель внутри), поэтому
apply() не нужна схема: она нужна только разбору и фасетам.
"""

import re
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import (
    BooleanField,
    Count,
    F,
    IntegerField,
    Max,
    Min,
    Q,
    QuerySet,
)
from django.db.models.fields.json import KeyTextTransform
from django.http import QueryDict

from .choices import Heating
from .models import Brand, Color, Variant
from .schema import COLORS, LIST, RANGE, Field

COLOR_KEY = 'color'
EXECUTION_KEY = 'execution'
MAX_NUMBER = Decimal(10**9)
YES, NO = 'да', 'нет'
# Подписи значений из attrs варианта, которые хранятся кодами
ATTR_LABELS: dict[str, dict[str, str]] = {
    'heating': {str(k): str(v) for k, v in Heating.choices},
}


def _number(raw: str | None) -> Decimal | None:
    try:
        value = Decimal((raw or '').strip())
    except InvalidOperation:
        return None
    if not value.is_finite() or abs(value) > MAX_NUMBER:
        return None
    return value


def _csv(raw: str | None) -> list[str]:
    return [part.strip() for part in (raw or '').split(',') if part.strip()]


def _model_field(source: str):
    if '__' in source:
        return None
    return Variant._meta.get_field(source)  # noqa: SLF001


def _is_int_column(source: str) -> bool:
    return isinstance(_model_field(source), IntegerField)


def _expression(source: str):
    if source.startswith('attrs__'):
        return KeyTextTransform(source.removeprefix('attrs__'), 'attrs')
    return F(source)


def _coerce(source: str, values: list[str]) -> list:
    if isinstance(_model_field(source), BooleanField):
        return [
            value.lower() == 'true'
            for value in values
            if value.lower() in ('true', 'false')
        ]
    if not _is_int_column(source):
        return values
    result = []
    for raw in values:
        try:
            result.append(int(raw))
        except ValueError:
            continue
    return result


def _execution(raw: str | None) -> list[tuple[int, str]]:
    result = []
    for part in _csv(raw):
        tubes, _, connection = part.partition('-')
        if re.fullmatch(r'[0-9]+', tubes):
            result.append((int(tubes), connection))
    return result


def _parse_range(params, field):
    low = _number(params.get(f'{field.key}_min'))
    high = _number(params.get(f'{field.key}_max'))
    if low is None and high is None:
        return None
    return (RANGE, field.source, field.divisor, low, high)


def _parse_list(params, field):
    values = _coerce(field.source, _csv(params.get(field.key)))
    return (LIST, field.source, values) if values else None


def _parse_colors(params, field):
    codes = _csv(params.get(field.key))
    if not codes:
        return None
    # Неизвестный код (устаревшая ссылка) — как будто его нет
    known = set(
        Color.objects.filter(code__in=codes).values_list('code', flat=True)
    )
    # Общая возможность запроса RAL не является записью обычного цвета.
    known.add('any-ral')
    codes = [code for code in codes if code in known]
    return (COLORS, field.source, codes) if codes else None


PARSERS = {
    RANGE: _parse_range,
    LIST: _parse_list,
    COLORS: _parse_colors,
}


def parse(params: QueryDict, fields: list[Field]) -> dict[str, tuple]:
    """Параметры запроса → {ключ: (вид, источник, ...)}. Мусор пропускается."""
    parsed: dict[str, tuple] = {}
    for field in fields:
        entry = PARSERS[field.kind](params, field) if field.filter else None
        if entry is not None:
            parsed[field.key] = entry
    execution = _execution(params.get(EXECUTION_KEY))
    if execution:
        parsed[EXECUTION_KEY] = (EXECUTION_KEY, '', execution)
    return parsed


def _with_colors(qs: QuerySet, codes: list[str]) -> QuerySet:
    """Цвет доступен варианту, если он в одной из его групп; пустой список
    групп — все группы серии."""
    explicit = Variant.objects.filter(color_groups__colors__code__in=codes)
    inherited = Variant.objects.filter(
        color_groups__isnull=True,
        series__color_groups__colors__code__in=codes,
    )
    return qs.filter(
        Q(pk__in=explicit.values('pk')) | Q(pk__in=inherited.values('pk'))
    )


def _apply_range(qs, key, entry):
    _, source, divisor, low, high = entry
    name = f'_f_{key}'
    qs = qs.alias(**{name: _expression(source)})
    if low is not None:
        qs = qs.filter(**{f'{name}__gte': low * divisor})
    if high is not None:
        qs = qs.filter(**{f'{name}__lte': high * divisor})
    return qs


def _apply_list(qs, key, entry):
    name = f'_f_{key}'
    return qs.alias(**{name: _expression(entry[1])}).filter(
        **{f'{name}__in': entry[2]}
    )


def _apply_colors(qs, key, entry):  # noqa: ARG001
    return _with_colors(qs, entry[2])


def _apply_execution(qs, key, entry):  # noqa: ARG001
    query = Q()
    for tubes, connection in entry[2]:
        tube_q = Q(tubes=tubes)
        if tubes == 0:
            tube_q |= Q(tubes__isnull=True)
        query |= tube_q & Q(connection=connection)
    return qs.filter(query)


APPLIERS = {
    RANGE: _apply_range,
    LIST: _apply_list,
    COLORS: _apply_colors,
    EXECUTION_KEY: _apply_execution,
}


def apply(
    qs: QuerySet,
    parsed: dict[str, tuple],
    *,
    skip: str | tuple[str, ...] | None = None,
) -> QuerySet:
    skipped = (skip,) if isinstance(skip, str) else skip or ()
    for key, entry in parsed.items():
        if key not in skipped:
            qs = APPLIERS[entry[0]](qs, key, entry)
    return qs


def _plain_number(value) -> int | float:
    value = Decimal(value)
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def range_steps(qs: QuerySet, fields: list[Field]) -> dict[str, list[int]]:
    """Размеры всей серии одним агрегатом; фронт кэширует с её деталями.

    Не вычисляется при фильтрации/пагинации таблицы. Цена и мощность могут
    иметь тысячи значений, поэтому для них остаётся обычный числовой ввод.
    """
    keys = {'height', 'width', 'depth', 'length', 'axis', 'sections'}
    aggregates = {
        field.key: ArrayAgg(
            field.source,
            distinct=True,
            order_by=field.source,
            filter=Q(**{f'{field.source}__isnull': False}),
        )
        for field in fields
        if field.kind == RANGE and field.filter and field.key in keys
    }
    if not aggregates:
        return {}
    return {
        key: values or []
        for key, values in qs.order_by().aggregate(**aggregates).items()
    }


def range_facets(qs: QuerySet, fields: list[Field]) -> dict[str, dict]:
    ranges = [f for f in fields if f.kind == RANGE and f.filter]
    if not ranges:
        return {}
    aggregates = {}
    for field in ranges:
        aggregates[f'{field.key}_lo'] = Min(_expression(field.source))
        aggregates[f'{field.key}_hi'] = Max(_expression(field.source))
    row = qs.order_by().aggregate(**aggregates)
    result = {}
    for field in ranges:
        low, high = row[f'{field.key}_lo'], row[f'{field.key}_hi']
        digits = Decimal('0.1') if field.divisor != 1 else Decimal(1)
        if low is not None:
            low = Decimal(low) / field.divisor
            low = _plain_number(low.quantize(digits, rounding=ROUND_FLOOR))
        if high is not None:
            high = Decimal(high) / field.divisor
            high = _plain_number(high.quantize(digits, rounding=ROUND_CEILING))
        result[field.key] = {
            'key': field.key,
            'label': field.label,
            'kind': RANGE,
            'unit': field.unit,
            'min': low,
            'max': high,
        }
    return result


def _value_labels(field: Field, values: list[str]) -> dict[str, str]:
    source = field.source
    if source.startswith('attrs__'):
        coded = ATTR_LABELS.get(source.removeprefix('attrs__'), {})
        return {
            value: coded.get(
                value, {'true': YES, 'false': NO}.get(value, value)
            )
            for value in values
        }
    if source == 'series__brand__slug':
        names = dict(
            Brand.objects.filter(slug__in=values).values_list('slug', 'name')
        )
        return {value: names.get(value, value) for value in values}
    model_field = _model_field(source)
    if isinstance(model_field, BooleanField):
        return {v: YES if v.lower() == 'true' else NO for v in values}
    if model_field is not None and model_field.choices:
        choices = {str(k): str(v) for k, v in model_field.choices}
        return {value: choices.get(value, value) for value in values}
    return {value: value for value in values}


def _sort_key(field: Field, value: str):
    model_field = _model_field(field.source)
    if model_field is not None and model_field.choices:
        order = [str(k) for k, _ in model_field.choices]
        return (0, order.index(value) if value in order else len(order), '')
    number = _number(value)
    if number is not None:
        return (1, number, '')
    return (2, 0, value)


def _own_filters(field: Field) -> tuple[str, ...]:
    # Чипы исполнений (execution) — тот же выбор, что трубность и подключение
    if field.key in ('tubes', 'connection'):
        return (field.key, EXECUTION_KEY)
    return (field.key,)


def _list_facet(qs: QuerySet, field: Field, parsed: dict) -> dict:
    rows = (
        apply(qs, parsed, skip=_own_filters(field))
        .annotate(_v=_expression(field.source))
        .exclude(_v__isnull=True)
    )
    if not _is_int_column(field.source):
        rows = rows.exclude(_v='')
    rows = rows.order_by().values('_v').annotate(n=Count('pk'))
    counts = {str(row['_v']): row['n'] for row in rows}
    values = sorted(counts, key=lambda v: _sort_key(field, v))
    labels = _value_labels(field, values)
    return {
        'key': field.key,
        'label': field.label,
        'kind': LIST,
        'values': [
            {'value': v, 'label': labels[v], 'count': counts[v]}
            for v in values
        ],
    }


def _color_facet(qs: QuerySet, field: Field, parsed: dict) -> dict:
    base = apply(qs, parsed, skip=field.key).order_by()
    counts: dict[str, int] = {}
    path = 'color_groups__colors__code'
    explicit = (
        base.filter(**{f'{path}__isnull': False})
        .values(path)
        .annotate(n=Count('pk', distinct=True))
    )
    for row in explicit:
        counts[row[path]] = counts.get(row[path], 0) + row['n']
    # Без своих групп вариант берёт все цвета серии. Соединять варианты с
    # цветами серии дорого (десятки тысяч строк на цвет), поэтому: варианты —
    # по сериям, цвета серий — из маленькой таблицы групп, сумма — здесь
    per_series = dict(
        base.filter(color_groups__isnull=True)
        .values_list('series_id')
        .annotate(n=Count('pk'))
    )
    series_colors = (
        Color.objects.filter(color_groups__series_id__in=per_series)
        .values_list('color_groups__series_id', 'code')
        .distinct()
    )
    for series_id, code in series_colors:
        counts[code] = counts.get(code, 0) + per_series[series_id]
    colors = Color.objects.filter(code__in=counts)
    return {
        'key': field.key,
        'label': field.label,
        'kind': COLORS,
        'values': [
            {
                'value': c.code,
                'label': c.name,
                'hex': c.hex,
                'count': counts[c.code],
            }
            for c in colors
        ],
    }


def facets(
    qs: QuerySet,
    fields: list[Field],
    parsed: dict[str, tuple],
) -> list[dict]:
    """qs — все активные варианты категории. Диапазоны не сужаются, счётчики
    списков считаются с остальными фильтрами, но без своего."""
    ranges = range_facets(qs, fields)
    result = []
    for field in fields:
        if not field.filter:
            continue
        if field.kind == RANGE:
            facet = ranges[field.key]
            # Диапазон без значений или из одной точки фильтровать нечем
            if facet['min'] is None or facet['min'] == facet['max']:
                continue
        elif field.kind == LIST:
            facet = _list_facet(qs, field, parsed)
        elif field.kind == COLORS:
            facet = _color_facet(qs, field, parsed)
        else:
            continue
        if field.kind != RANGE and not facet['values']:
            continue
        result.append(facet)
    return result
