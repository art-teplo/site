from decimal import Decimal

import pytest

from apps.catalog import schema
from apps.catalog.configurations import configured_price
from apps.catalog.models import (
    Brand,
    Category,
    ColorGroup,
    ConnectionOption,
    Series,
    Variant,
)


@pytest.fixture
def offers(db):  # noqa: ARG001
    brand = Brand.objects.create(slug='kzto', name='КЗТО')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    series = Series.objects.create(
        brand=brand,
        category=category,
        slug='test',
        name='Test',
        offer_mode='configured',
        markup_percent=Decimal('10'),
        is_published=True,
    )
    group = ColorGroup.objects.create(
        series=series, name='Стандарт', is_base=True, percent=Decimal('10')
    )
    variant = Variant.objects.create(
        series=series,
        article='Г25005',
        sections=5,
        tubes=2,
        price=Decimal('33697'),
        currency='RUB',
        price_byn=Decimal('1347.88'),
        thermovalve=False,
        connection='side',
    )
    baseline = ConnectionOption.objects.create(
        series=series,
        source_id='base',
        tubes=2,
        mount='wall',
        thermovalve=False,
        connection='side',
        label='Боковое',
        surcharge_rub=0,
        checked_on='2026-11-18',
        allowed_sections=[3, 4, 5, 6, 7],
    )
    bottom = ConnectionOption.objects.create(
        series=series,
        source_id='bottom',
        tubes=2,
        mount='wall',
        thermovalve=True,
        connection='bottom_center',
        label='Центральное',
        surcharge_rub=6007,
        base_adjustment_rub=2785,
        checked_on='2026-11-18',
        allowed_sections=[4, 5, 6, 7],
    )
    return series, variant, group, baseline, bottom


@pytest.mark.django_db
def test_global_catalog_sees_configured_connections(client, offers):
    from django.urls import reverse  # noqa: PLC0415

    _series, _variant, _group, _baseline, bottom = offers
    response = client.get(
        reverse('series-list'),
        {'category': 'radiatory', 'connection': 'bottom_center'},
    )
    assert response.status_code == 200
    assert response.json()['count'] == 1
    data = client.get(
        reverse('series-variants', args=['test']),
        {'execution': f'kzto-{bottom.pk}', 'thermovalve': 'false'},
    ).json()
    assert data['count'] == 0
    assert (
        client.get(
            reverse('variant-detail', args=['Г25005']),
            {
                'series': 'test',
                'execution': f'kzto-{bottom.pk}',
                'thermovalve': 'false',
            },
        ).status_code
        == 404
    )


@pytest.mark.django_db
def test_sql_offer_price_matches_reference_without_multiplying_fixed_fees(
    offers,
):
    from apps.catalog.offers import offer_query  # noqa: PLC0415

    _series, variant, group, _, bottom = offers
    rate = Decimal('0.036432')
    rows = offer_query(Variant.objects.all(), color=None, rate=rate).page(
        1, 20
    )
    assert len(rows) == 2
    actual = next(
        r for r in rows if r['configuration_key'] == f'kzto-{bottom.pk}'
    )
    assert actual['price'] == configured_price(
        variant, bottom, {group.pk: group}, rate=rate
    )
    assert actual['thermovalve'] is True
    assert actual['connection'] == 'bottom_center'
    assert Variant.objects.get(pk=variant.pk).connection == 'side'


@pytest.mark.django_db
def test_rules_apply_sections_and_all_filters_to_the_same_offer(offers):
    from apps.catalog.offers import offer_query  # noqa: PLC0415

    series, _variant, _, _, _ = offers
    Variant.objects.create(
        series=series,
        article='three',
        tubes=2,
        sections=3,
        price=1,
        currency='RUB',
    )
    q = offer_query(Variant.objects.all(), color=None, rate=Decimal('0.04'))
    assert q.count() == 3
    both = {
        'connection': (schema.LIST, 'connection', ['bottom_center']),
        'thermovalve': (schema.LIST, 'thermovalve', [False]),
    }
    assert q.filter(both).count() == 0
    assert q.filter({'connection': both['connection']}).count() == 1


@pytest.mark.django_db
def test_direct_price_and_unknown_attributes_are_preserved(offers):
    from apps.catalog.offers import offer_query  # noqa: PLC0415

    series, _, _, _, _ = offers
    series.offer_mode = 'direct'
    series.factory_orientation = 'v'
    series.save()
    Variant.objects.all().update(thermovalve=None)
    q = offer_query(Variant.objects.all(), color=None)
    assert q.count() == 1  # добавленные правила не дублируют прямую строку
    row = q.page(1, 20)[0]
    assert row['price'] == 1483
    assert row['orientation'] == 'v'
    assert row['thermovalve'] is None
    assert (
        q.filter(
            {'thermovalve': (schema.LIST, 'thermovalve', [False])}
        ).count()
        == 0
    )


@pytest.mark.django_db
def test_any_ral_and_missing_rate_do_not_return_numeric_quotes(offers):
    from apps.catalog.offers import offer_query  # noqa: PLC0415

    series, *_ = offers
    ral = ColorGroup.objects.create(series=series, name='RAL', any_ral=True)
    q = offer_query(
        Variant.objects.all(), color=f'any-{ral.pk}', rate=Decimal('0.04')
    )
    assert all(r['price'] is None for r in q.page(1, 20))
    assert all(
        r['price'] is None
        for r in offer_query(
            Variant.objects.all(), color=None, rate=None
        ).page(1, 20)
    )


@pytest.mark.django_db
def test_colour_facet_uses_each_colours_own_price(offers):
    from apps.catalog.models import Color  # noqa: PLC0415
    from apps.catalog.offers import offer_query  # noqa: PLC0415

    series, variant, base, *_ = offers
    series.offer_mode = 'direct'
    series.save()
    variant.price_byn = 100
    variant.save()
    base.percent = 0
    base.save()
    white = Color.objects.create(code='white', name='Белый', hex='#ffffff')
    black = Color.objects.create(code='black', name='Чёрный', hex='#000000')
    base.colors.set([white])
    paid = ColorGroup.objects.create(series=series, name='Платный', percent=20)
    paid.colors.set([black])
    q = offer_query(Variant.objects.all()).filter(
        {'price': (schema.RANGE, 'price_byn', 1, None, 110)}
    )
    facet = q.colour_facet(schema.COLOR)
    assert [v['value'] for v in facet['values']] == ['white']


@pytest.mark.django_db
def test_global_catalog_honours_structured_direct_execution(offers, client):
    series, variant, *_ = offers
    series.offer_mode = 'direct'
    series.save()
    variant.mount = 'floor'
    variant.thermovalve = None
    variant.save()
    data = client.get(
        '/api/series/',
        {'category': 'radiatory', 'execution': 'direct:2:side:wall:u'},
    ).json()
    assert data['count'] == 0


@pytest.mark.django_db
def test_any_ral_table_filters_group_availability_but_detail_can_request(
    offers,
):
    from apps.catalog.offers import query_for_series  # noqa: PLC0415

    series, variant, group, *_ = offers
    ral = ColorGroup.objects.create(series=series, name='Any', any_ral=True)
    variant.color_groups.set([group])
    query, _ = query_for_series(series, {'color': f'any-{ral.pk}'})
    assert query.count() == 0
    detail, _ = query_for_series(
        series, {'color': f'any-{ral.pk}'}, detail=True
    )
    assert detail.count() > 0
    assert detail.page(1, 1)[0]['price'] is None
