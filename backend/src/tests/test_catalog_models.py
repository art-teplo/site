import io
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from PIL import Image

from apps.catalog.admin import SeriesAdmin
from apps.catalog.models import (
    Brand,
    Category,
    Color,
    ColorGroup,
    CurrencyRate,
    Series,
    Variant,
)
from apps.catalog.pricing import in_color, recalculate, to_byn
from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend


@pytest.mark.parametrize(
    ('price', 'currency', 'rate', 'markup', 'expected'),
    [
        (
            Decimal('5480.00'),
            'RUB',
            Decimal('0.036399'),
            Decimal('0'),
            Decimal('199.47'),
        ),
        (
            Decimal('89.16'),
            'EUR',
            Decimal('3.3703'),
            Decimal('10'),
            Decimal('330.55'),
        ),
        (Decimal('100'), 'BYN', None, Decimal('5'), Decimal('105.00')),
        (Decimal('100'), 'RUB', None, Decimal('0'), None),
        (None, 'BYN', None, Decimal('0'), None),
    ],
)
def test_to_byn(price, currency, rate, markup, expected):
    assert to_byn(price, currency, rate, markup) == expected


def test_in_color_rounds_to_whole_byn():
    group = ColorGroup(percent=Decimal('15'))
    assert in_color(Decimal('199.47'), group) == 229
    assert in_color(Decimal('199.47'), ColorGroup(percent=Decimal('0'))) == 199


def test_in_color_any_ral_is_on_request():
    group = ColorGroup(percent=Decimal('0'), any_ral=True)
    assert in_color(Decimal('199.47'), group) is None
    assert in_color(None, ColorGroup(percent=Decimal('0'))) is None


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / 'media'


def png():
    buffer = io.BytesIO()
    Image.new('RGB', (4, 3)).save(buffer, 'PNG')
    return SimpleUploadedFile('c.png', buffer.getvalue(), 'image/png')


@pytest.fixture
def brand(db):  # noqa: ARG001
    return Brand.objects.create(
        slug='guardo',
        name='Guardo',
        note='n',
        warranty_years=10,
    )


@pytest.fixture
def category(db):  # noqa: ARG001
    return Category.objects.create(
        slug='panel',
        name='Панельные',
        short='к',
        image=png(),
        image_alt='a',
    )


@pytest.fixture
def series(brand, category):
    return Series.objects.create(
        brand=brand,
        category=category,
        slug='retta',
        name='Retta',
    )


def test_one_base_group_per_series(series):
    ColorGroup.objects.create(series=series, name='Базовые', is_base=True)
    ColorGroup.objects.create(series=series, name='Прочие')
    with pytest.raises(IntegrityError), transaction.atomic():
        ColorGroup.objects.create(series=series, name='Ещё', is_base=True)


def test_article_unique_within_brand(series, category):
    other_brand = Brand.objects.create(slug='nova', name='Nova', note='n')
    other = Series.objects.create(
        brand=other_brand,
        category=category,
        slug='nova',
        name='Nova',
    )
    Variant.objects.create(series=series, brand=series.brand, article='A1')
    Variant.objects.create(series=other, brand=other_brand, article='A1')
    with pytest.raises(IntegrityError), transaction.atomic():
        Variant.objects.create(series=series, brand=series.brand, article='A1')


def test_recalculate_uses_latest_rate_and_series_markup(series):
    brand = series.brand
    series.markup_percent = Decimal('10')
    series.save()
    CurrencyRate.objects.create(
        currency='RUB',
        rate=Decimal('0.010000'),
        date='2026-11-01',
    )
    CurrencyRate.objects.create(
        currency='RUB',
        rate=Decimal('0.020000'),
        date='2026-11-10',
    )
    variant = Variant.objects.create(
        series=series,
        brand=brand,
        article='A1',
        price=Decimal('1000'),
        currency='RUB',
    )
    byn = Variant.objects.create(
        series=series,
        brand=brand,
        article='A2',
        price=Decimal('100'),
    )
    assert CurrencyRate.latest('RUB') == Decimal('0.020000')

    assert recalculate() == 2

    variant.refresh_from_db()
    byn.refresh_from_db()
    assert variant.price_byn == Decimal('22.00')
    assert byn.price_byn == Decimal('110.00')


def test_variant_save_does_not_revalidate(
    series,
    django_capture_on_commit_callbacks,
):
    with (
        patch.object(revalidate_frontend, 'delay') as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        Variant.objects.create(series=series, brand=series.brand, article='A')
    delay.assert_not_called()


def test_muted_revalidation_suppresses_series_signal(
    brand,
    category,
    django_capture_on_commit_callbacks,
):
    with (
        patch.object(revalidate_frontend, 'delay') as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        with muted_revalidation():
            Series.objects.create(
                brand=brand,
                category=category,
                slug='s1',
                name='S1',
            )
        delay.assert_not_called()
        Series.objects.create(
            brand=brand,
            category=category,
            slug='s2',
            name='S2',
        )
    delay.assert_called_once_with(Tag.CATALOG)


def test_series_warranty_falls_back_to_brand(series):
    assert series.warranty == 10
    series.warranty_years = 5
    assert series.warranty == 5
    series.warranty_years = None
    series.brand.warranty_years = None
    assert series.warranty is None


def test_color_save_revalidates_catalog(
    db,  # noqa: ARG001
    django_capture_on_commit_callbacks,
):
    with (
        patch.object(revalidate_frontend, 'delay') as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        Color.objects.create(code='RAL 9016', name='Белый', hex='#f6f6f6')
    delay.assert_called_once_with(Tag.CATALOG)


def test_variant_str_adds_connection(series):
    plain = Variant.objects.create(series=series, article='A')
    rotated = Variant.objects.create(
        series=series, article='B', connection='bottom_ends'
    )
    assert str(plain) == 'A'
    assert str(rotated) == 'B · нижнее по краям'


def test_series_admin_brand_change_moves_variants(series, brand):
    other = Brand.objects.create(slug='nova', name='Nova', note='n')
    variant = Variant.objects.create(
        series=series, article='A', price=Decimal('100'), currency='BYN'
    )
    series.brand = other
    series.markup_percent = Decimal('10')

    SeriesAdmin(Series, AdminSite()).save_model(
        None, series, SimpleNamespace(changed_data=['brand']), True
    )

    variant.refresh_from_db()
    assert variant.brand == other
    assert variant.price_byn == Decimal('110.00')
    assert brand.pk != other.pk


def test_series_markup_change_does_not_reprice_other_series(series, category):
    other = Series.objects.create(
        brand=series.brand,
        category=category,
        name='Pilon',
        slug='pilon',
    )
    selected = Variant.objects.create(
        series=series, article='A', price=Decimal('100')
    )
    untouched = Variant.objects.create(
        series=other, article='B', price=Decimal('100')
    )
    other.markup_percent = Decimal('5')
    other.save()
    recalculate()
    series.markup_percent = Decimal('20')
    SeriesAdmin(Series, AdminSite()).save_model(
        None, series, SimpleNamespace(changed_data=['markup_percent']), True
    )
    selected.refresh_from_db()
    untouched.refresh_from_db()
    assert selected.price_byn == Decimal('120.00')
    assert untouched.price_byn == Decimal('105.00')
