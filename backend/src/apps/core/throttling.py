from rest_framework.throttling import AnonRateThrottle


class ProxiedAnonRateThrottle(AnonRateThrottle):
    """Лимит для запросов из интернета; серверные запросы Next к бэку — нет.

    Next ходит на бэк напрямую (http://backend:8000), без nginx, и все его
    запросы пришли бы с одного IP — на общий лимит. nginx же всегда
    дописывает X-Forwarded-For и единственный открыт наружу, так что запрос
    без этого заголовка — внутренний.
    """

    def allow_request(self, request, view):
        if 'HTTP_X_FORWARDED_FOR' not in request.META:
            return True
        return super().allow_request(request, view)
