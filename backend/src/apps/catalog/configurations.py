"""Проекция базового артикула в подтверждённое подключение КЗТО."""

from copy import copy
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count

from . import serializers
from .models import CurrencyRate
from .pricing import available_groups, effective_percent, to_byn, whole_byn

UNSET_RATE = object()


def option_for_key(series, key):
    if not key.startswith('kzto-') or not key[5:].isdigit():
        return None
    return series.connection_options.filter(pk=int(key[5:])).first()


def eligible(variants, option):
    return variants.filter(
        tubes=option.tubes, sections__in=option.allowed_sections
    )


def executions(series, variants):
    counts = {
        (r['tubes'], r['sections']): r['count']
        for r in variants.order_by()
        .values('tubes', 'sections')
        .annotate(count=Count('pk'))
    }
    result = []
    for option in series.connection_options.all():
        count = sum(
            counts.get((option.tubes, n), 0) for n in option.allowed_sections
        )
        if count:
            result.append(
                {
                    'key': f'kzto-{option.pk}',
                    'tubes': option.tubes,
                    'connection': option.connection,
                    'label': option.label,
                    'source_id': option.source_id,
                    'mount': option.mount,
                    'thermovalve': option.thermovalve,
                    'count': count,
                }
            )
    # Базовое подключение — первым; затем частые ряды и конкретные варианты.
    result.sort(
        key=lambda r: (
            r['connection'] != 'side' and r['connection'] != 'bottom_ends',
            -r['count'],
            r['tubes'],
            r['key'],
        )
    )
    return result


def _group(variant, groups, color):
    available = available_groups(variant, groups)
    if color and color.startswith('any-'):
        return next(
            (g for g in available if g.any_ral and color == f'any-{g.pk}'),
            None,
        )
    if color:
        return next(
            (
                g
                for g in available
                if any(c.code == color for c in g.colors.all())
            ),
            None,
        )
    return next((g for g in available if g.is_base), None) or min(
        (g for g in available if not g.any_ral),
        key=effective_percent,
        default=None,
    )


def configured_price(variant, option, groups, color=None, *, rate=UNSET_RATE):
    if (
        variant.price is None
        or option.surcharge_rub is None
        or variant.currency != 'RUB'
    ):
        return None
    group = _group(variant, groups, color)
    if groups and (group is None or group.any_ral):
        return None
    percent = effective_percent(group) if group else 0
    rub = (Decimal(variant.price) * (100 + percent) / Decimal(100)).quantize(
        Decimal(1), rounding=ROUND_HALF_UP
    )
    rub += option.surcharge_rub + option.base_adjustment_rub
    if rate is UNSET_RATE:
        rate = CurrencyRate.latest('RUB')
    return whole_byn(to_byn(rub, 'RUB', rate, variant.series.markup_percent))


def price_matches(price, entry):
    if entry is None:
        return True
    low, high = entry[3:]
    return (
        price is not None
        and (low is None or price >= low)
        and (high is None or price <= high)
    )


def configured_row(variant, option, price):
    projected = copy(variant)
    projected.connection, projected.thermovalve, projected.mount = (
        option.connection,
        option.thermovalve,
        option.mount,
    )
    data = serializers.row(projected, price)
    # Обычный пересчёт цвета на фронте умножил бы и фиксированную доплату.
    data.pop('price_byn', None)
    data['configuration_label'] = option.label
    data['configuration_key'] = f'kzto-{option.pk}'
    return data


def variant_response(series, variants, params, fields, option):  # noqa: ARG001
    from .offers import variant_response as response  # noqa: PLC0415

    if option is None:
        return {'count': 0, 'results': [], 'facets': [], 'price_from': None}
    selected = params.copy()
    selected['execution'] = f'kzto-{option.pk}'
    return response(series, variants, selected)


def detail_response(series, variants, params, fields):  # noqa: ARG001
    from .offers import detail_response as response  # noqa: PLC0415

    return response(series, variants, params)
