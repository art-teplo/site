import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def health(request):  # noqa: ARG001
    """Живы ли Django, Postgres и Redis — для healthcheck docker и деплоя."""
    checks = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        checks['db'] = 'ok'
    except Exception:
        logger.exception('health: БД недоступна')
        checks['db'] = 'error'
    try:
        cache.set('health', 'ok', timeout=5)
        checks['cache'] = 'ok' if cache.get('health') == 'ok' else 'error'
    except Exception:
        logger.exception('health: кэш недоступен')
        checks['cache'] = 'error'

    ok = all(value == 'ok' for value in checks.values())
    return JsonResponse(
        {
            'status': 'ok' if ok else 'error',
            'version': settings.VERSION,
            **checks,
        },
        status=200 if ok else 503,
    )
