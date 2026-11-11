from decimal import ROUND_HALF_UP, Decimal

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


def in_color(price_byn: Decimal | None, group) -> int | None:
    """Цена в группе цветов, целые BYN; None — «по запросу»."""
    if price_byn is None or group.any_ral:
        return None
    value = price_byn * (1 + group.percent / 100)
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


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
