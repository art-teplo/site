import logging

from celery import shared_task

from apps.content.models import Tag
from apps.content.tasks import revalidate_frontend

from .models import CurrencyRate, Variant
from .pricing import recalculate
from .rates import fetch_rate

logger = logging.getLogger(__name__)

CURRENCIES = ('RUB', 'EUR', 'USD')


@shared_task
def update_rates() -> list[str]:
    """Тянет курсы Нацбанка и пересчитывает цены в BYN."""
    updated = []
    for code in CURRENCIES:
        try:
            day, rate = fetch_rate(code)
        except Exception:
            logger.exception('Не удалось получить курс %s', code)
            continue
        CurrencyRate.objects.update_or_create(
            currency=code,
            date=day,
            defaults={'rate': rate},
        )
        updated.append(code)
    if updated:
        recalculate(Variant.objects.filter(currency__in=updated))
        revalidate_frontend.delay(Tag.CATALOG)
    return updated
