from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework.throttling import AnonRateThrottle

from apps.core.throttling import ProxiedAnonRateThrottle


def test_throttle_ignores_spoofed_forwarded_for():
    request = APIRequestFactory().get(
        '/api/health/',
        HTTP_X_FORWARDED_FOR='6.6.6.6, 203.0.113.7',
        REMOTE_ADDR='172.18.0.5',
    )

    ident = AnonRateThrottle().get_ident(request)

    assert ident == '203.0.113.7'


class TinyThrottle(ProxiedAnonRateThrottle):
    rate = '2/min'


def _request(**meta):
    return Request(APIRequestFactory().get('/api/health/', **meta))


def test_internal_requests_without_forwarded_for_are_not_throttled():
    internal = _request()
    assert all(TinyThrottle().allow_request(internal, None) for _ in range(6))


def test_requests_with_forwarded_for_are_throttled():
    external = _request(HTTP_X_FORWARDED_FOR='203.0.113.7')
    results = [TinyThrottle().allow_request(external, None) for _ in range(3)]
    assert results == [True, True, False]
