from decimal import Decimal

import pytest

from apps.catalog.importers import kzto
from apps.catalog.importers.kzto import RADIATOR, TARGETS
from apps.catalog.kzto_split import apply_kzto_split, plan_kzto_split
from apps.catalog.models import (
    Brand,
    Category,
    Color,
    ColorGroup,
    Series,
    Showcase,
    Variant,
)
from apps.content.tasks import revalidate_frontend
from tests.test_catalog_kzto import feed, radiator


def test_factory_radiators_have_28_independent_series():
    radiators = [
        target for target in TARGETS.values() if target.kind == RADIATOR
    ]
    assert len(radiators) == 28
    assert len({target.slug for target in radiators}) == 28
    assert TARGETS['QUADRUM NEO 50 H'].slug == 'kzto-quadrum-neo-50-h'
    assert TARGETS['QUADRUM NEO 50 V'].slug == 'kzto-quadrum-neo-50-v'
    assert len({target.slug for target in TARGETS.values()}) == 39


@pytest.mark.django_db
def test_split_preserves_variants_prices_colours_and_is_repeatable(tmp_path):

    brand = Brand.objects.create(slug='kzto', name='КЗТО')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    old = Series.objects.create(
        brand=brand,
        category=category,
        slug='kzto-quadrum-30',
        name='Quadrum 30',
        is_published=True,
        markup_percent=17,
    )
    group = ColorGroup.objects.create(series=old, name='Базовый', is_base=True)
    colour = Color.objects.create(code='RAL 9016', name='Белый', hex='#ffffff')
    group.colors.add(colour)
    variant = Variant.objects.create(
        series=old,
        article='К30В13003',
        orientation='v',
        connection='side',
        price=Decimal('9000'),
        price_byn=Decimal('301.23'),
    )
    variant.color_groups.add(group)
    showcase = Showcase.objects.create(
        series=old, variant=variant, label='Вертикальный'
    )
    source = tmp_path / 'feed.xml'
    source.write_bytes(
        feed(
            radiator(3, 2, 'Quadrum 30 V 1-300-3', variant.article, '9000', 3)
        )
    )
    plan = plan_kzto_split(feed_source=str(source))
    assert Series.objects.count() == 1
    apply_kzto_split(plan)
    variant.refresh_from_db()
    old.refresh_from_db()
    showcase.refresh_from_db()
    assert variant.series.slug == 'kzto-quadrum-30-v'
    assert variant.price_byn == Decimal('301.23')
    assert variant.series.markup_percent == 17
    assert not old.is_published
    assert showcase.series_id == variant.series_id
    new_group = variant.color_groups.get()
    assert new_group.series_id == variant.series_id
    assert list(new_group.colors.all()) == [colour]
    apply_kzto_split(plan_kzto_split(feed_source=str(source)))
    assert Variant.objects.count() == 1
    assert Series.objects.count() == 3
    assert ColorGroup.objects.count() == 3


@pytest.mark.django_db
def test_split_ambiguous_orientation_aborts_before_writing(tmp_path):
    brand = Brand.objects.create(slug='kzto', name='КЗТО')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    old = Series.objects.create(
        brand=brand,
        category=category,
        slug='kzto-quadrum-30',
        name='Quadrum 30',
    )
    Variant.objects.create(series=old, article='unknown', orientation='')
    source = tmp_path / 'feed.xml'
    source.write_bytes(feed())
    with pytest.raises(kzto.FeedError):
        plan_kzto_split(feed_source=str(source))
    assert Series.objects.count() == 1


@pytest.mark.django_db
def test_old_series_link_resolves_by_article_without_defaulting_to_vertical(
    client,
):
    brand = Brand.objects.create(slug='kzto', name='КЗТО', is_published=True)
    category = Category.objects.create(
        slug='radiatory', name='Радиаторы', is_published=True
    )
    for suffix, orientation in [('v', 'v'), ('h', 'h')]:
        series = Series.objects.create(
            slug=f'kzto-quadrum-neo-50-{suffix}',
            name=f'NEO {suffix}',
            brand=brand,
            category=category,
            is_published=True,
        )
        Variant.objects.create(
            series=series,
            article=f'NEO-{suffix}',
            orientation=orientation,
            connection='side',
        )
    url = '/api/series/kzto-quadrum-neo-50/legacy/'
    result = client.get(url).json()
    assert len(result['choices']) == 2
    assert result['target'] is None
    assert (
        client.get(url, {'v': 'NEO-h'}).json()['target']
        == 'kzto-quadrum-neo-50-h'
    )


@pytest.mark.django_db
def test_duplicate_colour_group_names_abort_split_before_writes(tmp_path):
    brand = Brand.objects.create(slug='kzto', name='КЗТО')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    old = Series.objects.create(
        brand=brand, category=category, slug='kzto-quadrum-30', name='Old'
    )
    ColorGroup.objects.create(series=old, name='Муар', percent=10)
    ColorGroup.objects.create(series=old, name='Муар', percent=20)
    source = tmp_path / 'feed.xml'
    source.write_bytes(feed())
    with pytest.raises(kzto.FeedError):
        plan_kzto_split(feed_source=str(source))
    assert Series.objects.count() == 1


@pytest.mark.django_db
def test_split_invalidates_once_on_commit(
    tmp_path, monkeypatch, django_capture_on_commit_callbacks
):

    brand = Brand.objects.create(slug='kzto', name='КЗТО')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    old = Series.objects.create(
        brand=brand, category=category, slug='kzto-quadrum-30', name='Old'
    )
    Variant.objects.create(
        series=old, article='К30В13003', orientation='v', connection='side'
    )
    source = tmp_path / 'feed.xml'
    source.write_bytes(
        feed(radiator(3, 2, 'Quadrum 30 V 1-300-3', 'К30В13003', '9000', 3))
    )
    calls = []
    monkeypatch.setattr(
        revalidate_frontend, 'delay', lambda tag: calls.append(tag)
    )
    with django_capture_on_commit_callbacks(execute=True):
        apply_kzto_split(plan_kzto_split(feed_source=str(source)))
    assert calls == ['catalog']


@pytest.mark.django_db
def test_legacy_redirect_preserves_specific_connection_rule(client):
    from apps.catalog.models import ConnectionOption  # noqa: PLC0415

    brand = Brand.objects.create(slug='kzto', name='КЗТО')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    series = Series.objects.create(
        brand=brand,
        category=category,
        slug='kzto-quadrum-neo-50-h',
        name='H',
        is_published=True,
        offer_mode='configured',
    )
    Variant.objects.create(
        series=series, article='H-3', tubes=1, sections=3, connection='side'
    )
    for code, conn in [('side', 'side'), ('left', 'bottom_center')]:
        rule = ConnectionOption.objects.create(
            series=series,
            source_id=code,
            label=code,
            tubes=1,
            mount='wall',
            connection=conn,
            thermovalve=False,
            surcharge_rub=0,
            allowed_sections=[3],
            checked_on='2026-11-18',
        )
        if code == 'left':
            wanted = rule.pk
    data = client.get(
        '/api/series/kzto-quadrum-neo-50/legacy/',
        {'v': 'H-3', 'execution': f'kzto-{wanted}'},
    ).json()
    assert data['execution'] == f'kzto-{wanted}'
