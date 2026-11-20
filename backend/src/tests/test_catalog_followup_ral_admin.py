import pytest
from django.contrib import admin
from django.urls import reverse

from apps.catalog.admin import SeriesAdmin
from apps.catalog.models import Brand, Category, ColorGroup, Series, Variant


@pytest.fixture
def paint_catalog(db):  # noqa: ARG001
    brand = Brand.objects.create(slug='brand', name='Бренд')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    series = []
    for number in range(3):
        s = Series.objects.create(
            brand=brand,
            category=category,
            slug=f's{number}',
            name=f'S{number}',
            is_published=True,
        )
        v = Variant.objects.create(
            series=s,
            article=f'V{number}',
            price=100,
            currency='BYN',
            price_byn=100,
        )
        ColorGroup.objects.create(series=s, name='Базовый', is_base=True)
        if number < 2:
            ColorGroup.objects.create(series=s, name='Любой RAL', any_ral=True)
            if number == 1:
                # Явный набор групп не разрешает у этого артикула RAL.
                v.color_groups.add(s.color_groups.get(is_base=True))
        series.append(s)
    return series


def test_catalog_ral_filters_real_availability_and_returns_request_price(
    client,
    paint_catalog,  # noqa: ARG001
):
    data = client.get(
        '/api/series/', {'category': 'radiatory', 'color': 'any-ral'}
    ).json()
    assert {c['series'] for c in data['results']} == {'s0'}
    assert data['results'][0]['price_from'] is None
    assert any(c['code'] == 'any-ral' for c in data['results'][0]['colors'])


def test_catalog_ral_facet_counts_eligible_offers_not_series_groups(
    client,
    paint_catalog,  # noqa: ARG001
):
    data = client.get('/api/series/', {'category': 'radiatory'}).json()
    colors = next(f for f in data['facets'] if f['key'] == 'color')['values']
    ral = next(v for v in colors if v['value'] == 'any-ral')
    assert ral['count'] == 1
    assert 'gradient' in ral['hex']
    filtered = client.get(
        '/api/series/',
        {'category': 'radiatory', 'color': 'any-ral', 'price_max': '1000'},
    ).json()
    assert filtered['count'] == 0
    # Самоснятие цвета сохраняет price_max: неизвестная цена RAL не становится числом.
    assert not any(
        v['value'] == 'any-ral'
        for f in filtered['facets']
        if f['key'] == 'color'
        for v in f['values']
    )


def test_generic_ral_reaches_series_table_and_detail(client, paint_catalog):
    s = paint_catalog[0]
    data = client.get(
        f'/api/series/{s.slug}/variants/', {'color': 'any-ral'}
    ).json()
    assert data['count'] == 1
    assert data['results'][0]['price'] is None
    data = client.get(
        '/api/variants/V0/', {'series': s.slug, 'color': 'any-ral'}
    ).json()
    assert data['price'] is None


def test_admin_direct_connections_link_points_to_source_variants(
    paint_catalog,
):
    s = paint_catalog[0]
    link = str(SeriesAdmin(Series, admin.site).connections_link(s))
    assert reverse('admin:catalog_variant_changelist') in link
    assert 'series__id__exact=' + str(s.pk) in link
    assert reverse('admin:catalog_connectionoption_changelist') not in link


def test_admin_configured_connections_link_points_to_rules(paint_catalog):
    s = paint_catalog[0]
    s.offer_mode = 'configured'
    link = str(SeriesAdmin(Series, admin.site).connections_link(s))
    assert reverse('admin:catalog_connectionoption_changelist') in link
