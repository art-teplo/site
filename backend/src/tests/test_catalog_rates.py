import io
import json
from datetime import date
from decimal import Decimal
from urllib.error import URLError

import pytest

from apps.catalog import rates, tasks
from apps.catalog.models import Brand, Category, CurrencyRate, Series, Variant
from apps.catalog.pricing import recalculate
from apps.catalog.rates import fetch_rate
from apps.content.models import Tag

NBRB_RUB = (
    b'{"Cur_ID":456,"Date":"2026-11-11T00:00:00","Cur_Abbreviation":"RUB",'
    b'"Cur_Scale":100,"Cur_OfficialRate":3.6399}'
)


def nbrb(code, scale, rate):
    return json.dumps(
        {
            'Cur_ID': 1,
            'Date': '2026-11-11T00:00:00',
            'Cur_Abbreviation': code,
            'Cur_Scale': scale,
            'Cur_OfficialRate': rate,
        },
    ).encode()


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def fake_urlopen(bodies):
    def urlopen(url, timeout=None):  # noqa: ARG001
        body = bodies[url.split('/rates/')[1].split('?')[0]]
        if isinstance(body, Exception):
            raise body
        return Response(body)

    return urlopen


@pytest.fixture
def variant(db):  # noqa: ARG001
    brand = Brand.objects.create(name='Б', slug='b')
    category = Category.objects.create(name='К', slug='k')
    series = Series.objects.create(brand=brand, category=category, name='С')
    return Variant.objects.create(
        series=series,
        brand=brand,
        article='A1',
        price=Decimal('5480'),
        currency='RUB',
    )


def test_fetch_rate_divides_by_scale(monkeypatch):
    monkeypatch.setattr(rates, 'urlopen', fake_urlopen({'RUB': NBRB_RUB}))

    assert fetch_rate('RUB') == (date(2026, 11, 11), Decimal('0.036399'))


def test_update_rates_saves_and_recalculates(
    variant,
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    monkeypatch.setattr(
        rates,
        'urlopen',
        fake_urlopen(
            {
                'RUB': NBRB_RUB,
                'EUR': nbrb('EUR', 1, 3.3703),
                'USD': nbrb('USD', 1, 2.9),
            },
        ),
    )
    calls = []
    monkeypatch.setattr(
        tasks.revalidate_frontend,
        'delay',
        lambda tag: calls.append(tag),
    )

    with django_capture_on_commit_callbacks(execute=True):
        result = tasks.update_rates()

    variant.refresh_from_db()
    assert result == ['RUB', 'EUR', 'USD']
    assert CurrencyRate.objects.count() == 3
    assert variant.price_byn == Decimal('199.47')
    assert calls == [Tag.CATALOG]


@pytest.mark.usefixtures('variant')
def test_update_rates_is_idempotent_per_day(monkeypatch):
    monkeypatch.setattr(
        rates,
        'urlopen',
        fake_urlopen({'RUB': NBRB_RUB, 'EUR': NBRB_RUB, 'USD': NBRB_RUB}),
    )
    monkeypatch.setattr(tasks.revalidate_frontend, 'delay', lambda _tag: None)

    tasks.update_rates()
    tasks.update_rates()

    assert CurrencyRate.objects.filter(currency='RUB').count() == 1


def test_update_rates_keeps_old_rate_when_api_down(variant, monkeypatch):
    CurrencyRate.objects.create(
        currency='RUB',
        rate=Decimal('0.036399'),
        date=date(2026, 11, 10),
    )
    recalculate()
    monkeypatch.setattr(
        rates,
        'urlopen',
        fake_urlopen(
            {code: URLError('down') for code in ('RUB', 'EUR', 'USD')},
        ),
    )
    calls = []
    monkeypatch.setattr(
        tasks.revalidate_frontend,
        'delay',
        lambda tag: calls.append(tag),
    )

    assert tasks.update_rates() == []

    variant.refresh_from_db()
    assert variant.price_byn == Decimal('199.47')
    assert CurrencyRate.objects.count() == 1
    assert calls == []


@pytest.mark.usefixtures('variant')
def test_one_currency_failing_does_not_stop_others(monkeypatch):
    monkeypatch.setattr(
        rates,
        'urlopen',
        fake_urlopen(
            {
                'RUB': NBRB_RUB,
                'EUR': URLError('down'),
                'USD': nbrb('USD', 1, 2.9),
            },
        ),
    )
    monkeypatch.setattr(tasks.revalidate_frontend, 'delay', lambda _tag: None)

    assert tasks.update_rates() == ['RUB', 'USD']


def test_no_rate_means_price_on_request(variant):
    variant.price_byn = Decimal('1')
    variant.save()

    recalculate()

    variant.refresh_from_db()
    assert variant.price_byn is None
