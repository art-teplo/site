from rest_framework.test import APIRequestFactory
from rest_framework.throttling import AnonRateThrottle


def test_throttle_ignores_spoofed_forwarded_for():
    request = APIRequestFactory().get(
        '/api/health/',
        HTTP_X_FORWARDED_FOR='6.6.6.6, 203.0.113.7',
        REMOTE_ADDR='172.18.0.5',
    )

    ident = AnonRateThrottle().get_ident(request)

    assert ident == '203.0.113.7'
