from decimal import Decimal

import pytest

from apps.catalog.models import (
    Brand,
    Category,
    ConnectionOption,
    Series,
    Variant,
)


@pytest.fixture
def option(db):  # noqa: ARG001
    brand = Brand.objects.create(slug='kzto', name='КЗТО')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    series = Series.objects.create(
        slug='rs', name='РС', brand=brand, category=category
    )
    Variant.objects.create(series=series, article='three', tubes=5, sections=3)
    Variant.objects.create(series=series, article='five', tubes=5, sections=5)
    return ConnectionOption.objects.create(
        series=series,
        source_id='source',
        label='Напольный',
        tubes=5,
        mount='floor',
        connection='side',
        thermovalve=False,
        surcharge_rub=100,
        base_adjustment_rub=2785,
        allowed_sections=[3, 5],
        checked_on='2026-11-18',
        source_url='https://kztoradiator.ru/rs/',
    )


@pytest.mark.django_db
def test_admin_combined_surcharge_preserves_installation_component(option):
    from apps.catalog.admin_forms import ConnectionOptionForm  # noqa: PLC0415

    form = ConnectionOptionForm(
        instance=option,
        data={
            'series': option.series_id,
            'label': 'Напольный',
            'tubes': 5,
            'mount': 'floor',
            'connection': 'side',
            'allowed_sections': ['3', '5'],
            'configuration_surcharge_rub': '3000',
        },
    )
    assert form.is_valid(), form.errors
    result = form.save()
    assert result.surcharge_rub == Decimal('215')
    assert result.base_adjustment_rub == 2785
    assert result.allowed_sections == [3, 5]


@pytest.mark.django_db
def test_admin_rejects_invalid_sections_and_surcharge_below_installation(
    option,
):
    from apps.catalog.admin_forms import ConnectionOptionForm  # noqa: PLC0415

    form = ConnectionOptionForm(
        instance=option,
        data={
            'series': option.series_id,
            'label': 'x',
            'tubes': 5,
            'mount': 'floor',
            'connection': 'side',
            'allowed_sections': ['4'],
            'configuration_surcharge_rub': '2000',
        },
    )
    assert not form.is_valid()
    assert 'allowed_sections' in form.errors
    assert 'configuration_surcharge_rub' in form.errors


@pytest.mark.django_db
def test_connection_model_rejects_non_integer_or_duplicate_section_values(
    option,
):
    from django.core.exceptions import ValidationError  # noqa: PLC0415

    for values in [[True], [3, 3], [0], [3, 4], []]:
        option.allowed_sections = values
        with pytest.raises(ValidationError):
            option.full_clean()


@pytest.mark.django_db
def test_editing_baseline_cannot_hide_active_sizes(option):
    from django.core.exceptions import ValidationError  # noqa: PLC0415

    option.surcharge_rub = 0
    option.save()
    option.series.offer_mode = 'configured'
    option.series.save()
    option.allowed_sections = [3]
    with pytest.raises(ValidationError, match='покры'):
        option.full_clean()


@pytest.mark.django_db
def test_existing_rule_cannot_be_transferred_to_another_series(option):
    from apps.catalog.admin_forms import ConnectionOptionForm  # noqa: PLC0415

    original_series_id = option.series_id
    other = Series.objects.create(
        slug='other',
        name='Other',
        brand=option.series.brand,
        category=option.series.category,
    )
    Variant.objects.create(series=other, article='other', tubes=5, sections=3)
    form = ConnectionOptionForm(
        instance=option,
        data={
            'series': other.pk,
            'label': option.label,
            'tubes': 5,
            'mount': 'floor',
            'connection': 'side',
            'allowed_sections': ['3'],
            'configuration_surcharge_rub': '3000',
        },
    )
    assert form.is_valid(), form.errors
    assert form.save().series_id == original_series_id
