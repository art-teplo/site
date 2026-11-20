import json

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

from apps.catalog import models


@pytest.fixture
def series(db):  # noqa: ARG001
    brand = models.Brand.objects.create(slug='velar', name='Velar')
    category = models.Category.objects.create(
        slug='radiatory', name='Радиаторы'
    )
    return models.Series.objects.create(
        slug='velar-p30', name='P30', brand=brand, category=category
    )


@pytest.mark.django_db
def test_family_must_match_series_brand_and_category(series):
    assert hasattr(models, 'ProductFamily'), 'Нет общей линейки'
    other = models.Brand.objects.create(slug='other', name='Other')
    family = models.ProductFamily.objects.create(
        brand=other, category=series.category, key='p30', name='P30'
    )
    series.family = family
    with pytest.raises(ValidationError, match='бренд'):
        series.full_clean()
    family.brand = series.brand
    family.category = models.Category.objects.create(
        slug='armatura', name='Арматура'
    )
    family.save()
    with pytest.raises(ValidationError, match='категор'):
        series.full_clean()


@pytest.mark.django_db
def test_unknown_valve_is_unknown_and_factory_orientation_is_not_shape(series):
    variant = models.Variant.objects.create(
        series=series, article='V270-14', height_mm=270, width_mm=680
    )
    assert variant.thermovalve is None
    assert hasattr(series, 'factory_orientation')
    series.factory_orientation = 'v'
    series.save()
    assert variant.effective_orientation == 'v'
    variant.orientation = 'h'
    with pytest.raises(ValidationError, match='Положен'):
        variant.full_clean()


@pytest.mark.django_db
def test_first_connection_rule_does_not_change_offer_mode(series):
    assert getattr(series, 'offer_mode', None) == 'direct'
    models.ConnectionOption.objects.create(
        series=series,
        source_id='one',
        label='Боковое',
        tubes=1,
        mount='wall',
        connection='side',
        allowed_sections=[3],
        checked_on='2026-11-18',
        surcharge_rub=0,
    )
    series.refresh_from_db()
    assert series.offer_mode == 'direct'
    models.Variant.objects.create(
        series=series, article='uncovered', tubes=1, sections=4
    )
    series.offer_mode = 'configured'
    with pytest.raises(ValidationError, match='покры'):
        series.full_clean()


@pytest.mark.django_db
def test_family_audit_report_rolls_back_and_apply_is_repeatable(
    series, tmp_path
):
    report = tmp_path / 'audit.json'
    call_command('audit_catalog_attributes', report=str(report))
    series.refresh_from_db()
    assert series.family_id is None
    assert json.loads(report.read_text())['changes']
    call_command('audit_catalog_attributes', report=str(report), apply=True)
    series.refresh_from_db()
    assert series.family.key == 'p30'
    call_command('audit_catalog_attributes', report=str(report), apply=True)
    assert json.loads(report.read_text())['changes'] == []


def test_family_registry_does_not_invent_horizontal_nova_or_pilon():
    from apps.catalog.importers.product_families import family_for_target  # noqa: PLC0415

    for brand, slug in [('nova', 'nova-siluet'), ('guardo', 'guardo-pilon')]:
        assert family_for_target(brand, slug)['orientation'] == ''
    assert family_for_target('velar', 'velar-p30')['orientation'] == ''
    assert (
        family_for_target('kzto', 'kzto-quadrum-neo-50-h')['orientation']
        == 'h'
    )


@pytest.mark.django_db
def test_reimport_preserves_manual_family_and_reports_orientation_conflict(
    series,
):
    from apps.catalog.importers.product_families import assign_family  # noqa: PLC0415

    family = models.ProductFamily.objects.create(
        brand=series.brand,
        category=series.category,
        key='confirmed',
        name='Подтверждено',
    )
    series.family = family
    series.factory_orientation = 'h'
    series.save()
    assign_family(series)
    series.refresh_from_db()
    assert series.family_id == family.pk
    assert series.factory_orientation == 'h'
    series.slug = 'velar-q40'
    with pytest.raises(ValueError, match='Положение'):
        assign_family(series)


@pytest.mark.django_db
def test_import_does_not_overwrite_confirmed_traits_or_contradict_series(
    series,
):
    from apps.catalog.importers.product_families import import_traits  # noqa: PLC0415

    variant = models.Variant.objects.create(
        series=series,
        article='manual',
        mount='floor',
        attrs={'confirmed_fields': ['mount']},
    )
    assert (
        import_traits(series, {'mount': '', 'orientation': 'v'}, variant)[
            'mount'
        ]
        == 'floor'
    )
    series.factory_orientation = 'h'
    with pytest.raises(ValueError, match='Положение'):
        import_traits(series, {'orientation': 'v'}, None)
