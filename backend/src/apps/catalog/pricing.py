from collections.abc import Iterable
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from django.db.models import QuerySet

from .choices import Currency
from .models import CurrencyRate, Variant

KOPECK = Decimal('0.01')
BATCH_SIZE = 500


def to_byn(
    price: Decimal | None,
    currency: str,
    rate: Decimal | None,
    markup: Decimal,
) -> Decimal | None:
    """Цена прайса в BYN с наценкой бренда, до копеек."""
    if price is None:
        return None
    if currency != Currency.BYN:
        if rate is None:
            return None
        price *= rate
    price *= 1 + markup / 100
    return price.quantize(KOPECK, rounding=ROUND_HALF_UP)


def effective_percent(group) -> int:
    """Процент группы цветов: только целый и не меньше нуля (решение
    владельца), дробный округляется вверх."""
    return max(0, int(group.percent.to_integral_value(ROUND_CEILING)))


def in_color(price_byn: Decimal | None, group) -> int | None:
    """Цена в группе цветов, целые BYN; None — «по запросу»."""
    if price_byn is None or group.any_ral:
        return None
    value = price_byn * (100 + effective_percent(group)) / 100
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def whole_byn(value: Decimal | None) -> int | None:
    if value is None:
        return None
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def available_groups(variant, groups: dict) -> list:
    """Группы цветов варианта (нужен prefetch color_groups); пустой список —
    все группы серии."""
    explicit = [
        groups[g.pk] for g in variant.color_groups.all() if g.pk in groups
    ]
    return explicit or list(groups.values())


def base_price(price_byn: Decimal | None, available: list) -> int | None:
    """Цена варианта без выбранного цвета (R8): базовая группа, если она
    доступна, иначе самая дешёвая из доступных (не any_ral); у серии без
    групп — цена варианта."""
    if not available:
        return whole_byn(price_byn)
    group = next((g for g in available if g.is_base), None)
    if group is None:
        group = min(
            (g for g in available if not g.any_ral),
            key=effective_percent,
            default=None,
        )
    return None if group is None else in_color(price_byn, group)


def price_from(
    offers: Iterable[tuple[Decimal | None, list]],
    group=None,
) -> int | None:
    """Цена «от» по вариантам: пары (price_byn, доступные группы).

    Без группы — минимум цен без выбранного цвета. С группой — минимум
    price_byn среди вариантов, где она доступна, в цене этой группы (процент
    монотонен); any_ral — по запросу."""
    if group is None:
        prices = [base_price(price, avail) for price, avail in offers]
        return min((p for p in prices if p is not None), default=None)
    known = [
        price
        for price, avail in offers
        if price is not None and any(g.pk == group.pk for g in avail)
    ]
    return in_color(min(known), group) if known else None


def recalculate(variants: QuerySet | None = None) -> int:
    """Пересчитывает price_byn по последним курсам и наценке брендов."""
    if variants is None:
        variants = Variant.objects.all()
    rates = {
        currency: CurrencyRate.latest(currency)
        for currency in Currency.values
        if currency != Currency.BYN
    }
    batch = []
    total = 0
    queryset = variants.select_related('brand').order_by('pk')
    for variant in queryset.iterator(chunk_size=BATCH_SIZE):
        variant.price_byn = to_byn(
            variant.price,
            variant.currency,
            rates.get(variant.currency),
            variant.brand.markup_percent,
        )
        batch.append(variant)
        if len(batch) >= BATCH_SIZE:
            Variant.objects.bulk_update(batch, ['price_byn'])
            total += len(batch)
            batch = []
    if batch:
        Variant.objects.bulk_update(batch, ['price_byn'])
        total += len(batch)
    return total
