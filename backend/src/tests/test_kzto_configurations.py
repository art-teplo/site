from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.http import QueryDict

from apps.catalog import configurations, schema
from apps.catalog.configurations import configured_price
from apps.catalog.models import (
    Brand,
    Category,
    Color,
    ColorGroup,
    ConnectionOption,
    CurrencyRate,
    Series,
    Variant,
)
from apps.content.tasks import revalidate_frontend


@pytest.fixture
def configured_series(db):  # noqa: ARG001
    brand = Brand.objects.create(slug='kzto', name='КЗТО', is_published=True)
    category = Category.objects.create(
        slug='radiatory', name='Радиаторы', is_published=True
    )
    series = Series.objects.create(
        slug='kzto-garmoniya',
        name='Гармония',
        offer_mode='configured',
        brand=brand,
        category=category,
        is_published=True,
        markup_percent=Decimal('10'),
    )
    group = ColorGroup.objects.create(
        series=series, name='Матовый', percent=Decimal('10')
    )
    colour = Color.objects.create(
        code='RAL 9016M', name='Белый матовый', hex='#ffffff'
    )
    group.colors.add(colour)
    CurrencyRate.objects.create(
        currency='RUB', rate=Decimal('0.035'), date=date(2026, 11, 18)
    )
    variant = Variant.objects.create(
        series=series,
        article='Г25005',
        tubes=2,
        sections=5,
        height_mm=545,
        width_mm=351,
        orientation='v',
        connection='side',
        price=33697,
        currency='RUB',
        price_byn=Decimal('1297.33'),
    )
    rule = ConnectionOption.objects.create(
        series=series,
        source_id='1120',
        label='нижнее',
        tubes=2,
        connection='bottom_right',
        thermovalve=True,
        mount='wall',
        surcharge_rub=6007,
        allowed_sections=[4, 5, 6, 7],
        checked_on=date(2026, 11, 18),
        source_url='https://kztoradiator.ru/garmoniya-2-500-5',
    )
    return series, variant, rule, group


@pytest.mark.django_db
def test_fixed_addition_is_not_multiplied_by_colour(configured_series):
    _series, variant, rule, group = configured_series
    price = configured_price(variant, rule, {group.pk: group}, 'RAL 9016M')
    # round(33697*1.10) +6007 =43074 RUB; *0.035 *1.10 =1658.349 BYN
    assert price == 1658


@pytest.mark.django_db
def test_configuration_filters_sections_and_preserves_article(
    client, configured_series
):
    series, variant, rule, _group = configured_series
    Variant.objects.create(
        series=series,
        article='Г250015',
        tubes=2,
        sections=15,
        connection='side',
        price=84157,
        currency='RUB',
    )
    response = client.get(
        f'/api/series/{series.slug}/variants/',
        {
            'execution': f'kzto-{rule.pk}',
            'color': 'RAL 9016M',
            'price_min': 1600,
            'price_max': 1700,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data['count'] == 1
    row = data['results'][0]
    assert row['article'] == variant.article
    assert row['price'] == 1658
    assert row['connection'] == 'bottom_right'
    assert row['thermovalve']
    assert row['configuration_label'] == 'нижнее'
    assert (
        'price_byn' not in row
    )  # wait for server colour calculation, do not multiply the connection charge
    detail = client.get(
        f'/api/variants/{variant.article}/',
        {
            'series': series.slug,
            'execution': f'kzto-{rule.pk}',
            'color': 'RAL 9016M',
        },
    )
    assert detail.json()['price'] == 1658
    assert (
        client.get(
            '/api/variants/Г250015/',
            {'series': series.slug, 'execution': f'kzto-{rule.pk}'},
        ).status_code
        == 404
    )
    assert (
        client.get(
            f'/api/series/{series.slug}/variants/',
            {'execution': 'kzto-999999'},
        ).json()['count']
        == 0
    )


@pytest.mark.django_db
def test_floor_installation_addition_is_also_after_colour(configured_series):
    _series, variant, rule, group = configured_series
    variant.price = Decimal('78064')
    rule.base_adjustment_rub = Decimal('2785')
    rule.surcharge_rub = Decimal('0')
    assert (
        configured_price(variant, rule, {group.pk: group}, 'RAL 9016M') == 3413
    )


@pytest.mark.django_db
def test_any_ral_has_no_numeric_price_or_price_range(
    client, configured_series
):
    series, _variant, rule, _group = configured_series
    any_group = ColorGroup.objects.create(
        series=series, name='Любой RAL', any_ral=True
    )
    params = {'execution': f'kzto-{rule.pk}', 'color': f'any-{any_group.pk}'}
    data = client.get(f'/api/series/{series.slug}/variants/', params).json()
    assert data['count'] == 1
    assert data['price_from'] is None
    assert data['results'][0]['price'] is None
    assert all(f['key'] != 'price' for f in data['facets'])
    params['price_min'] = 1
    assert (
        client.get(f'/api/series/{series.slug}/variants/', params).json()[
            'count'
        ]
        == 0
    )


@pytest.mark.django_db
def test_selected_detail_respects_dimensions_but_retains_unavailable_colour(
    client, configured_series
):
    series, variant, rule, group = configured_series
    params = {
        'series': series.slug,
        'execution': f'kzto-{rule.pk}',
        'height_min': 600,
    }
    url = f'/api/variants/{variant.article}/'
    assert client.get(url, params).status_code == 404
    params.pop('height_min')
    params['price_max'] = 1
    assert client.get(url, params).status_code == 404
    params.pop('price_max')
    unavailable = Color.objects.create(
        code='Unavailable', name='Недоступный цвет', hex='#000000'
    )
    other = ColorGroup.objects.create(series=series, name='Другой')
    other.colors.add(unavailable)
    variant.color_groups.add(group)
    params['color'] = 'Unavailable'
    data = client.get(url, params).json()
    assert data['article'] == variant.article
    assert data['price'] is None


@pytest.mark.django_db
def test_missing_rate_is_queried_once_for_full_config_response(
    monkeypatch, configured_series
):

    series, _variant, rule, _group = configured_series
    calls = []

    def latest(_currency):
        calls.append(True)
        return

    monkeypatch.setattr(configurations.CurrencyRate, 'latest', latest)
    data = configurations.variant_response(
        series,
        Variant.objects.filter(series=series),
        QueryDict(''),
        schema.for_category('radiatory'),
        rule,
    )
    assert data['results'][0]['price'] is None
    assert len(calls) == 1


@pytest.mark.django_db
def test_legacy_retains_exact_depth_and_any_ral_group(
    client, configured_series
):
    series, variant, rule, _group = configured_series
    series.slug = 'kzto-quadrum-30-h'
    series.save()
    rule.surcharge_rub = 0
    rule.connection = 'bottom_ends'
    rule.save()
    old = Series.objects.create(
        slug='kzto-quadrum-30',
        name='Old',
        brand=series.brand,
        category=series.category,
    )
    old_any = ColorGroup.objects.create(
        series=old, name='Любой RAL', any_ral=True
    )
    new_any = ColorGroup.objects.create(
        series=series, name=old_any.name, any_ral=True, legacy_origin=old_any
    )
    params = {'v': variant.article, 'color': f'any-{old_any.pk}'}
    data = client.get('/api/series/kzto-quadrum-30/legacy/', params).json()
    assert data['execution'] == f'kzto-{rule.pk}'
    assert data['color'] == f'any-{new_any.pk}'


@pytest.mark.django_db
def test_connection_import_invalidates_once_and_keeps_manual_edits(
    monkeypatch, django_capture_on_commit_callbacks, configured_series
):

    series, _variant, rule, _group = configured_series
    calls = []
    monkeypatch.setattr(
        revalidate_frontend, 'delay', lambda tag: calls.append(tag)
    )
    with django_capture_on_commit_callbacks(execute=True):
        call_command('import_kzto_connections', '--series', series.slug)
    assert calls == []
    with django_capture_on_commit_callbacks(execute=True):
        call_command(
            'import_kzto_connections', '--series', series.slug, '--apply'
        )
    assert calls == ['catalog']
    calls.clear()
    rule.surcharge_rub = 7777
    rule.save()
    calls.clear()
    with django_capture_on_commit_callbacks(execute=True):
        call_command(
            'import_kzto_connections', '--series', series.slug, '--apply'
        )
    assert calls == []
    rule.refresh_from_db()
    assert rule.surcharge_rub == 7777
