# ruff: noqa: PLC0415
from decimal import Decimal
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

from apps.catalog.models import (
    Brand,
    Category,
    ColorGroup,
    Series,
    SeriesImage,
    Showcase,
    Variant,
)


def guardo_row(article, connection, height, width, *, power=158):
    return SimpleNamespace(
        series_slug='guardo-retta-3p',
        base_article=article,
        connection=connection,
        height_mm=height,
        width_mm=width,
        depth_mm=57,
        power_w=power,
        orientation='',
        mount='floor' if '-FL' in article else '',
    )


def test_factory_mapping_uses_connection_and_code_not_shape():
    from apps.catalog.importers.factory_editions import edition_for_row

    for row, orientation in [
        (guardo_row('3P-0500-03 BK-GOR', 'side', 130, 500), 'h'),
        (guardo_row('3P-0500-03 BK-GOR', 'bottom_ends', 500, 130), 'v'),
        (guardo_row('3P-0300-40 BK-VER', 'side', 300, 1980), 'v'),
        (guardo_row('3P-0500-03 NK-GOR-L-FL', 'bottom_left', 230, 500), 'h'),
        (guardo_row('3P-0500-03 E-L', 'electric_left', 500, 130), 'v'),
    ]:
        assert edition_for_row(row)['orientation'] == orientation
        assert row.height_mm in (130, 500, 300, 230)
    with pytest.raises(ValueError, match='Неизвест'):
        edition_for_row(guardo_row('3P-0500-03 XXX', 'side', 500, 130))


def velar_source(path):
    from tests.test_catalog_velar import sheet

    book = Workbook()
    book.remove(book.active)
    sheet(
        book,
        'P30 V',
        ['БП'],
        [('Velar P30 270 V - 14', 'P30 V', 270, 14, 680, 12440, 200, 50)],
    )
    sheet(
        book,
        'P30 H',
        ['БП'],
        [('Velar P30 270 H - 14', 'P30 H', 680, 14, 270, 14306, 200, 50)],
    )
    book.save(path)
    return path


@pytest.fixture
def split_fixture(db, tmp_path):  # noqa: ARG001
    brand = Brand.objects.create(slug='velar', name='Velar')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    series = Series.objects.create(
        brand=brand,
        category=category,
        slug='velar-p30',
        name='Velar P30',
        is_published=True,
        markup_percent=17,
    )
    group = ColorGroup.objects.create(series=series, name='RAL', any_ral=True)
    variants = []
    for o, h, w, p in [('v', 270, 680, 12440), ('h', 680, 270, 14306)]:
        v = Variant.objects.create(
            series=series,
            article=f'Velar P30 270 {o.upper()} - 14 БП RAL9016',
            connection='side',
            orientation=o,
            height_mm=h,
            width_mm=w,
            depth_mm=90,
            sections=14,
            power_w=500,
            price=p,
            price_byn=Decimal('555.55'),
            currency='RUB',
        )
        v.color_groups.add(group)
        variants.append(v)
    photo = SeriesImage.objects.create(
        series=series,
        image='images/stylish.jpg',
        image_width=1200,
        image_height=900,
        image_alt='Velar P30, вертикальный',
    )
    showcase = Showcase.objects.create(
        series=series, label='Наше превью', variant=variants[0]
    )
    return (
        series,
        variants,
        group,
        photo,
        showcase,
        velar_source(tmp_path / 'source.xlsx'),
    )


@pytest.mark.django_db
def test_plan_is_readonly_and_blocks_missing_source_or_changed_geometry(
    split_fixture,
):
    from apps.catalog.catalog_editions import plan_catalog_editions

    old, variants, _, _, _, source = split_fixture
    plan = plan_catalog_editions(source=source, series_slugs=[old.slug])
    assert not plan.conflicts
    assert len(plan.moves) == 2
    assert Series.objects.count() == 1
    assert {m['orientation'] for m in plan.moves} == {'h', 'v'}
    assert any('Q40' in str(e) for e in plan.exceptions)
    variants[0].height_mm = 271
    variants[0].save()
    assert plan_catalog_editions(
        source=source, series_slugs=[old.slug]
    ).conflicts


@pytest.mark.django_db
def test_apply_preserves_prices_pks_colors_and_presentation_and_is_repeatable(
    split_fixture,
):
    from apps.catalog import serializers
    from apps.catalog.catalog_editions import (
        apply_catalog_editions,
        plan_catalog_editions,
    )

    old, variants, group, photo, showcase, source = split_fixture
    original = serializers.card_image(showcase, old)
    plan = plan_catalog_editions(source=source, series_slugs=[old.slug])
    result = apply_catalog_editions(plan)
    assert result['moved'] == 2
    old.refresh_from_db()
    assert not old.is_published
    for v in variants:
        v.refresh_from_db()
        assert v.series.slug == f'velar-p30-{v.orientation}'
        assert v.series.markup_percent == 17
        assert v.price_byn == Decimal('555.55')
        assert list(v.color_groups.values_list('name', flat=True)) == [
            group.name
        ]
        assert v.series.family.presentation_photo_id == photo.pk
    assert [image.image.name for image in variants[0].series.images.all()] == [
        photo.image.name
    ]
    assert not variants[1].series.images.exists()
    showcase = Showcase.objects.get(pk=showcase.pk)
    assert serializers.card_image(showcase, variants[0].series) == original
    repeated = plan_catalog_editions(source=source, series_slugs=[old.slug])
    assert not repeated.conflicts
    assert apply_catalog_editions(repeated)['moved'] == 0


@pytest.mark.django_db
def test_apply_refuses_stale_plan_before_any_write(split_fixture):
    from apps.catalog.catalog_editions import (
        apply_catalog_editions,
        plan_catalog_editions,
    )

    old, variants, _, _, _, source = split_fixture
    plan = plan_catalog_editions(source=source, series_slugs=[old.slug])
    Variant.objects.filter(pk=variants[0].pk).update(price=1)
    with pytest.raises(ValueError, match='изменил'):
        apply_catalog_editions(plan)
    assert Series.objects.count() == 1
    assert old.variants.count() == 2


@pytest.mark.django_db
def test_legacy_h_link_remaps_any_ral_and_family_tile_keeps_style(
    split_fixture, client
):
    from apps.catalog import serializers
    from apps.catalog.catalog_editions import (
        apply_catalog_editions,
        plan_catalog_editions,
    )
    from apps.catalog.views import SeriesListView

    old, variants, group, _, _, source = split_fixture
    original = serializers.series_image(old)
    apply_catalog_editions(
        plan_catalog_editions(source=source, series_slugs=[old.slug])
    )
    data = client.get(
        f'/api/series/{old.slug}/legacy/',
        {
            'v': variants[1].article,
            'color': f'any-{group.pk}',
            'connection': 'side',
        },
    ).json()
    assert data['target'] == 'velar-p30-h'
    assert data['color'] != f'any-{group.pk}'
    tiles = SeriesListView.model_range('radiatory', ['velar'])
    assert len(tiles) == 1
    assert tiles[0]['image'] == original
    assert tiles[0]['name'] == old.name


@pytest.mark.django_db
def test_repeat_import_routes_to_children_instead_of_reviving_parent(
    split_fixture,
):
    from apps.catalog.catalog_editions import (
        apply_catalog_editions,
        plan_catalog_editions,
    )
    from apps.catalog.importers.velar import import_velar

    old, variants, _, _, _, source = split_fixture
    apply_catalog_editions(
        plan_catalog_editions(source=source, series_slugs=[old.slug])
    )
    Variant.objects.filter(pk=variants[0].pk).update(price=1)
    import_velar(source)
    assert old.variants.count() == 0
    assert Variant.objects.get(pk=variants[0].pk).price == 12440
    assert Variant.objects.count() == 2


@pytest.mark.django_db
def test_edition_api_links_real_siblings_and_hides_private_documents(
    split_fixture, client
):
    from apps.catalog.catalog_editions import (
        apply_catalog_editions,
        plan_catalog_editions,
    )
    from apps.catalog.models import SeriesFile

    old, _, _, _, _, source = split_fixture
    apply_catalog_editions(
        plan_catalog_editions(source=source, series_slugs=[old.slug])
    )
    target = Series.objects.get(slug='velar-p30-h')
    SeriesFile.objects.create(
        series=target,
        title='Скрытый',
        file='files/private.pdf',
        is_visible=False,
    )
    data = client.get('/api/series/velar-p30-h/').json()
    assert data['files'] == []
    assert {e['slug'] for e in data['editions']} == {
        'velar-p30-h',
        'velar-p30-v',
    }
    assert data['factory_orientation'] == 'h'


@pytest.mark.django_db
def test_plan_rejects_target_with_incompatible_factory_orientation(
    split_fixture,
):
    from apps.catalog.catalog_editions import plan_catalog_editions

    old, _, _, _, _, source = split_fixture
    Series.objects.create(
        brand=old.brand,
        category=old.category,
        slug='velar-p30-h',
        name='Wrong',
        factory_orientation='v',
    )
    assert plan_catalog_editions(
        source=source, series_slugs=[old.slug]
    ).conflicts


@pytest.mark.django_db
def test_project_link_changed_after_plan_aborts_transfer(split_fixture):
    from apps.catalog.catalog_editions import (
        apply_catalog_editions,
        plan_catalog_editions,
    )
    from apps.content.models import Project

    old, _, _, _, _, source = split_fixture
    plan = plan_catalog_editions(source=source, series_slugs=[old.slug])
    project = Project.objects.create(title='Ручной проект')
    project.series.add(old)
    with pytest.raises(ValueError, match='изменил'):
        apply_catalog_editions(plan)


@pytest.mark.django_db
def test_legacy_guardo_shared_article_is_resolved_by_connection(client):
    brand = Brand.objects.create(slug='guardo', name='Guardo')
    cat = Category.objects.create(slug='radiatory', name='Радиаторы')
    for o, conn in [('h', 'side'), ('v', 'bottom_ends')]:
        series = Series.objects.create(
            brand=brand,
            category=cat,
            slug=f'guardo-retta-3p-{o}',
            name=o,
            is_published=True,
        )
        Variant.objects.create(
            series=series,
            article='3P-0500-03 BK-GOR',
            connection=conn,
            orientation=o,
        )
    data = client.get(
        '/api/series/guardo-retta-3p/legacy/',
        {'v': '3P-0500-03 BK-GOR', 'connection': 'bottom_ends'},
    ).json()
    assert data['target'] == 'guardo-retta-3p-v'


@pytest.mark.django_db
def test_legacy_chooser_carries_remapped_colour_and_ranges_to_each_choice(
    split_fixture, client
):
    from urllib.parse import parse_qs

    from apps.catalog.catalog_editions import (
        apply_catalog_editions,
        plan_catalog_editions,
    )

    old, _, group, _, _, source = split_fixture
    apply_catalog_editions(
        plan_catalog_editions(source=source, series_slugs=[old.slug])
    )
    data = client.get(
        f'/api/series/{old.slug}/legacy/',
        {'color': f'any-{group.pk}', 'height_min': '100'},
    ).json()
    assert data['target'] is None
    for slug, query in data['queries'].items():
        parsed = parse_qs(query)
        assert parsed['height_min'] == ['100']
        assert parsed['color'] != [f'any-{group.pk}']
        assert Series.objects.get(slug=slug).color_groups.get(
            any_ral=True
        ).pk == int(parsed['color'][0][4:])


@pytest.mark.django_db
def test_old_any_ral_id_survives_renaming_the_copied_group(
    split_fixture, client
):
    from apps.catalog.catalog_editions import (
        apply_catalog_editions,
        plan_catalog_editions,
    )

    old, variants, _, _, _, source = split_fixture
    special = ColorGroup.objects.create(
        series=old, name='Особый RAL', percent=18, any_ral=True
    )
    apply_catalog_editions(
        plan_catalog_editions(source=source, series_slugs=[old.slug])
    )
    copied = ColorGroup.objects.get(
        series__slug='velar-p30-h', name=special.name
    )
    copied.name = 'Новое название'
    copied.percent = 21
    copied.save()
    data = client.get(
        f'/api/series/{old.slug}/legacy/',
        {'v': variants[1].article, 'color': f'any-{special.pk}'},
    ).json()
    assert data['color'] == f'any-{copied.pk}'


@pytest.mark.django_db
def test_velar_import_refuses_a_partially_split_parent_before_writing(
    split_fixture,
):
    from apps.catalog.importers.velar import import_velar

    old, variants, _, _, _, source = split_fixture
    Series.objects.create(
        brand=old.brand,
        category=old.category,
        slug='velar-p30-h',
        name='P30 H',
        factory_orientation='h',
    )
    original = list(
        Variant.objects.order_by('pk').values_list('pk', 'series_id', 'price')
    )
    with pytest.raises(ValueError, match='перенос'):
        import_velar(source)
    assert (
        list(
            Variant.objects.order_by('pk').values_list(
                'pk', 'series_id', 'price'
            )
        )
        == original
    )
    assert (
        Variant.objects.filter(
            pk__in=[v.pk for v in variants], series=old
        ).count()
        == 2
    )


@pytest.mark.django_db
def test_existing_migration_gets_audited_persistent_color_links(
    split_fixture, tmp_path
):
    import json

    from django.core.management import call_command

    from apps.catalog.catalog_editions import (
        apply_catalog_editions,
        plan_catalog_editions,
    )

    old, _, group, _, _, source = split_fixture
    apply_catalog_editions(
        plan_catalog_editions(source=source, series_slugs=[old.slug])
    )
    ColorGroup.objects.exclude(series=old).update(legacy_origin=None)
    report = tmp_path / 'origins.json'
    call_command('backfill_legacy_color_groups', report=report)
    assert len(json.loads(report.read_text())['links']) == 2
    assert (
        not ColorGroup.objects.exclude(series=old)
        .filter(legacy_origin__isnull=False)
        .exists()
    )
    call_command('backfill_legacy_color_groups', report=report, apply=True)
    assert ColorGroup.objects.filter(legacy_origin=group).count() == 2
    call_command('backfill_legacy_color_groups', report=report, apply=True)
    assert json.loads(report.read_text())['links'] == []
