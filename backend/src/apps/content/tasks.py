import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT = 10


@shared_task(
    autoretry_for=(URLError, TimeoutError),
    retry_backoff=True,
    max_retries=5,
)
def revalidate_frontend(tag: str):
    """Просит фронт обновить страницы с этим тегом кэша."""
    url = settings.FRONTEND__REVALIDATE_URL
    if not url:
        return
    request = Request(  # noqa: S310 — адрес из настроек, не от клиента
        url,
        data=json.dumps({'tags': [tag]}).encode(),
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {settings.FRONTEND__REVALIDATE_SECRET}',
        },
    )
    try:
        with urlopen(request, timeout=TIMEOUT):  # noqa: S310
            logger.info('Фронт обновит тег %s', tag)
    except HTTPError as error:
        if error.code < 500:
            logger.exception(
                'Фронт отклонил обновление тега %s: %s', tag, error.code
            )
            return
        raise
