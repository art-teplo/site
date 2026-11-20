from decimal import Decimal

import pytest

from apps.catalog import filters, schema
from apps.catalog.models import (
    Brand,
    Category,
    ConnectionOption,
    Series,
    Variant,
)
from apps.catalog.offers import (
    execution_metadata,
    offer_query,
    query_for_series,
)


@pytest.fixture
def direct_catalog(db):  # noqa: ARG001
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    brand = Brand.objects.create(slug='first', name='Первый')
    series = Series.objects.create(
        slug='first',
        name='Первый',
        brand=brand,
        category=category,
        is_published=True,
    )
    for article, height, width, mount, valve in [
        ('wall', 500, 400, 'wall', False),
        ('floor', 1000, 600, 'floor', False),
        ('valve', 1500, 800, 'wall', True),
    ]:
        Variant.objects.create(
            series=series,
            article=article,
            height_mm=height,
            width_mm=width,
            mount=mount,
            tubes=2,
            connection='side',
            thermovalve=valve,
            price_byn=height,
            price=height,
            currency='BYN',
            attrs={'voltage': '24' if height == 500 else '220'},
        )
    other_brand = Brand.objects.create(slug='second', name='Второй')
    other_series = Series.objects.create(
        slug='second',
        name='Второй',
        brand=other_brand,
        category=category,
        is_published=True,
    )
    Variant.objects.create(
        series=other_series,
        article='other',
        height_mm=3000,
        width_mm=1200,
        connection='bottom_center',
        price_byn=3000,
        price=3000,
    )
    return series


@pytest.mark.django_db
def test_range_facets_keep_brand_and_other_numeric_filters(direct_catalog):  # noqa: ARG001
    query = offer_query(Variant.objects.all()).filter(
        filters.parse(
            {'brand': 'first', 'height_min': '1000', 'width_max': '600'},
            schema.for_category('radiatory'),
        )
    )
    facets = query.range_facets([schema.HEIGHT, schema.WIDTH])
    assert (facets['height']['min'], facets['height']['max']) == (500, 1000)
    assert (facets['width']['min'], facets['width']['max']) == (600, 800)


@pytest.mark.django_db
def test_direct_execution_does_not_implicitly_select_mount(direct_catalog):
    query = offer_query(Variant.objects.filter(series=direct_catalog))
    executions = execution_metadata(query)
    assert len(executions) == 2
    plain = next(e for e in executions if e['thermovalve'] is False)
    assert plain['count'] == 2
    assert plain['mount'] is None
    selected = query.with_execution(plain['key']).page(1, 20)
    assert {row['article'] for row in selected} == {'wall', 'floor'}
    assert {row['price'] for row in selected} == {500, 1000}
    legacy = query.with_execution('direct:2:side:floor:f').page(1, 20)
    assert [row['article'] for row in legacy] == ['floor']


@pytest.mark.django_db
def test_mount_is_a_column_and_not_a_buyer_filter(direct_catalog):
    assert schema.MOUNT.column is True
    assert schema.MOUNT.filter is False
    query, _ = query_for_series(direct_catalog, {'mount': 'wall'})
    assert query.count() == 3


@pytest.mark.parametrize(
    'category_slug', ['konvektory', 'polotentsesushiteli']
)
@pytest.mark.django_db
def test_missing_connection_does_not_invent_execution(category_slug):
    category = Category.objects.create(slug=category_slug, name=category_slug)
    brand = Brand.objects.create(slug='brand', name='Brand')
    series = Series.objects.create(
        slug='sample',
        name='Sample',
        category=category,
        brand=brand,
    )
    Variant.objects.create(series=series, article='sample', thermovalve=False)
    assert execution_metadata(offer_query(Variant.objects.all())) == []


@pytest.mark.django_db
def test_dynamic_list_facets_retain_stable_cardinality(direct_catalog):
    voltage = schema.Field('voltage', 'Питание', schema.LIST, 'attrs__voltage')
    query = offer_query(Variant.objects.filter(series=direct_catalog)).filter(
        filters.parse(
            {'height_max': '500', 'voltage': '24'}, [schema.HEIGHT, voltage]
        )
    )
    facets = query.facets([voltage])
    assert facets[0]['total_values'] == 2
    assert facets[0]['values'] == [{'value': '24', 'label': '24', 'count': 1}]
    single = query.filter(
        {'height': (schema.RANGE, 'height_mm', 1, None, 500)}
    )
    assert single.facets([schema.TUBES])[0]['total_values'] == 1


@pytest.mark.django_db
def test_configured_execution_keys_and_mount_prices_stay_exact(direct_catalog):
    direct_catalog.offer_mode = 'configured'
    direct_catalog.save()
    Variant.objects.filter(series=direct_catalog).update(sections=5)
    rules = []
    for mount, surcharge in [('wall', 0), ('floor', 500)]:
        rules.append(
            ConnectionOption.objects.create(
                series=direct_catalog,
                source_id=mount,
                tubes=2,
                mount=mount,
                thermovalve=False,
                connection='side',
                label='Боковое',
                surcharge_rub=surcharge,
                checked_on='2026-11-19',
                allowed_sections=[5],
            )
        )
    Variant.objects.filter(series=direct_catalog).update(currency='RUB')
    query = offer_query(
        Variant.objects.filter(series=direct_catalog), rate=Decimal('1')
    )
    metadata = execution_metadata(query)
    assert {e['key'] for e in metadata} == {f'kzto-{r.pk}' for r in rules}
    assert len({e['label'] for e in metadata}) == 2
    prices = []
    for rule in rules:
        rows = query.with_execution(f'kzto-{rule.pk}').page(1, 20)
        assert {row['mount'] for row in rows} == {rule.mount}
        prices.append(rows[0]['price'])
    assert prices[1] - prices[0] == 500


@pytest.mark.django_db
def test_range_single_value_and_empty_active_facet_remain_available(
    direct_catalog,
):
    query = offer_query(Variant.objects.filter(series=direct_catalog)).filter(
        filters.parse({'height_max': '500'}, [schema.HEIGHT])
    )
    width = query.facets([schema.WIDTH])[0]
    assert (width['min'], width['max'], width['total_values']) == (400, 400, 3)
    voltage = schema.Field('voltage', 'Питание', schema.LIST, 'attrs__voltage')
    empty = query.filter(
        filters.parse(
            {'height_max': '1', 'voltage': '24'}, [schema.HEIGHT, voltage]
        )
    )
    facets = empty.facets([schema.WIDTH, voltage])
    assert facets[0]['min'] is None
    assert facets[1]['key'] == 'voltage'
    assert facets[1]['values'] == []


@pytest.mark.django_db
def test_partly_unknown_attribute_is_not_a_confirmed_series_constant(
    direct_catalog,
):
    variants = Variant.objects.filter(series=direct_catalog)
    variants.update(attrs={})
    variants.filter(article='wall').update(attrs={'fan': 'false'})
    field = schema.Field('fan', 'Вентилятор', schema.LIST, 'attrs__fan')
    facet = offer_query(variants).facets([field])[0]
    assert facet['total_values'] == 1
    assert facet['has_unknown'] is True
    assert facet['values'] == [{'value': 'false', 'label': 'нет', 'count': 1}]
