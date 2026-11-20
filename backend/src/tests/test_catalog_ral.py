from decimal import Decimal

import pytest

from apps.catalog.finishes import ensure_any_ral, supports_any_ral
from apps.catalog.models import Brand, Category, Series, Variant
from apps.catalog.pricing import available_groups, base_price


@pytest.mark.django_db
@pytest.mark.parametrize('brand_slug', ['kzto', 'radimax'])
def test_adding_any_ral_preserves_uncoloured_price(brand_slug):
    brand = Brand.objects.create(slug=brand_slug, name=brand_slug)
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    series = Series.objects.create(
        brand=brand, category=category, slug='test', name='Test'
    )
    variant = Variant.objects.create(
        series=series, article='one', price_byn=Decimal('826')
    )
    assert base_price(variant.price_byn, []) == 826
    ensure_any_ral(series)
    groups = {g.pk: g for g in series.color_groups.all()}
    assert (
        base_price(variant.price_byn, available_groups(variant, groups)) == 826
    )
    assert series.color_groups.filter(any_ral=True).count() == 1
    ensure_any_ral(series)
    assert series.color_groups.count() == 2


@pytest.mark.django_db
def test_other_brands_and_categories_are_unchanged():
    brand = Brand.objects.create(slug='velar', name='Velar')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    series = Series.objects.create(
        brand=brand, category=category, slug='velar-q80', name='Q80'
    )
    assert not supports_any_ral(series)
    assert not ensure_any_ral(series)
    assert not series.color_groups.exists()
    series.slug = 'velar-p30'
    assert not supports_any_ral(series)
    brand.slug = 'kzto'
    brand.save()
    assert supports_any_ral(series)
    category.slug = 'armatura'
    category.save()
    assert not supports_any_ral(series)
