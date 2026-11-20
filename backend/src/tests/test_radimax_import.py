from decimal import Decimal

import pytest

from apps.catalog.importers.radimax import (
    build_variants,
    import_radimax,
    read_price,
)
from apps.catalog.models import Brand, Category, Series, Subcategory, Variant


def test_radimax_loft_mounts_share_price():
    rows = list(build_variants(read_price()))
    loft = {
        row['mount']: row
        for row in rows
        if row['article'].startswith('LOFT-350-')
        and row['article'].endswith('-20')
        and '070' not in row['article']
    }
    assert {
        mount: (row['height_mm'], row['depth_mm'], row['price'])
        for mount, row in loft.items()
    } == {'wall': (430, 110, 3500), 'floor': (500, 129, 3500)}


def test_radimax_soul_limits_and_still_fixed_sizes():
    rows = list(build_variants(read_price()))
    soul = [row for row in rows if row['article'].startswith('SOUL-500-')]
    assert {row['sections'] for row in soul} == set(range(1, 26))
    assert {row['sections'] for row in soul if row['is_active']} == set(
        range(3, 26)
    )
    assert soul[-1]['price'] == 2275
    lynn = [row for row in rows if row['series'] == 'radimax-lynn']
    assert {row['sections'] for row in lynn if row['is_active']} == set(
        range(2, 16)
    )
    azhur = [row for row in rows if row['article'].startswith('STILL-AZHUR-')]
    assert all(row['is_active'] for row in azhur)
    assert {row['sections']: row['price'] for row in azhur} == {
        5: 750,
        7: 1050,
        8: 1200,
        10: 1500,
        12: 1800,
        14: 2100,
    }
    assert azhur[0]['width_mm'] == 383
    assert azhur[0]['attrs']['source_width_mm'] == str(Decimal('382.5'))


def test_radimax_has_one_card_per_factory_model():
    rows = list(build_variants(read_price()))
    series = {row['series'] for row in rows}
    assert len(series) == 33
    assert {
        slug for slug in series if slug.startswith('radimax-bristol-')
    } == {
        'radimax-bristol-300',
        'radimax-bristol-600',
        'radimax-bristol-800',
    }
    assert series.isdisjoint({'radimax-heat-300', 'radimax-derby-200'})
    assert len(rows) == 1237
    assert all(row['price'] > 0 for row in rows)


@pytest.mark.django_db
def test_radimax_split_reuses_variant_and_manual_availability():
    brand = Brand.objects.create(slug='radimax', name='Радимакс')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    parent = Series.objects.create(
        brand=brand,
        category=category,
        slug='radimax-loft',
        name='Радимакс Loft',
    )
    row = next(
        row
        for row in build_variants(read_price())
        if row['article'] == 'LOFT-350-WALL-20'
    )
    variant = Variant.objects.create(
        series=parent, article=row['article'], is_active=False
    )
    assert import_radimax([row])['updated'] == 1
    variant.refresh_from_db()
    assert variant.series.slug == 'radimax-loft-350'
    assert not variant.is_active
    assert variant.price_byn == Decimal('3500')
    assert import_radimax([row])['unchanged'] == 1


@pytest.mark.django_db
def test_radimax_uses_existing_cast_iron_and_steel_types():
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    cast_iron = Subcategory.objects.create(
        category=category, slug='chugunnye', name='Чугунные'
    )
    steel = Subcategory.objects.create(
        category=category, slug='stalnye', name='Стальные'
    )
    brand = Brand.objects.create(slug='radimax', name='Радимакс')
    soul = Series.objects.create(
        slug='radimax-soul-300',
        brand=brand,
        category=category,
        name='Соул 300',
    )
    variants = [
        row
        for row in build_variants(read_price())
        if row['article'] in ('SOUL-300-1', 'STILL-AZHUR-5')
    ]

    result = import_radimax(variants)
    assert result['reclassified'] == 1
    assert result['ral_added'] == 2
    soul.refresh_from_db()
    assert soul.subcategory == cast_iron
    still = Series.objects.get(slug='radimax-still-azhur')
    assert still.subcategory == steel
    assert still.color_groups.get(is_base=True).colors.count() == 4
    assert still.color_groups.filter(any_ral=True).count() == 1
    result = import_radimax(variants)
    assert result['reclassified'] == 0
    assert result['ral_added'] == 0
