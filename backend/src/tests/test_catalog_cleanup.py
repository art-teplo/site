# ruff: noqa: PLC0415
import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.catalog.models import (
    Brand,
    Category,
    ColorGroup,
    ProductFamily,
    Series,
    SeriesFile,
    SeriesImage,
    Showcase,
    Variant,
)
from apps.content.models import Project


@pytest.fixture
def cleanup_series(db):  # noqa: ARG001
    brand = Brand.objects.create(slug='kzto', name='КЗТО')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    parent = Series.objects.create(
        brand=brand,
        category=category,
        slug='kzto-quadrum-40',
        name='Quadrum 40',
        is_published=False,
    )
    children = [
        Series.objects.create(
            brand=brand,
            category=category,
            slug=f'kzto-quadrum-40-{orientation}',
            name=f'Quadrum 40 {orientation}',
            factory_orientation=orientation,
            is_published=True,
        )
        for orientation in ('v', 'h')
    ]
    return parent, children


def cleanup(tmp_path, name, *, apply=False):
    path = tmp_path / name
    call_command('cleanup_catalog_presentations', report=path, apply=apply)
    return json.loads(path.read_text())


@pytest.mark.django_db
def test_report_is_read_only_and_apply_preserves_media_and_family_reference(
    cleanup_series,
    tmp_path,
):
    parent, children = cleanup_series
    image = SeriesImage.objects.create(
        series=parent,
        image='retained/style.jpg',
        image_width=1600,
        image_height=1200,
    )
    document = SeriesFile.objects.create(
        series=parent,
        file='retained/catalog.pdf',
        title='Каталог',
    )
    family = ProductFamily.objects.create(
        brand=parent.brand,
        category=parent.category,
        key='quadrum-40',
        name='Quadrum 40',
        presentation_photo=image,
    )
    report = cleanup(tmp_path, 'report.json')
    assert Series.objects.filter(pk=parent.pk).exists()
    image = SeriesImage.objects.get(pk=image.pk)
    assert image.series_id == parent.pk
    assert report['parents'][0]['status'] == 'eligible'

    report = cleanup(tmp_path, 'backup.json', apply=True)
    assert not Series.objects.filter(pk=parent.pk).exists()
    image = SeriesImage.objects.get(pk=image.pk)
    document.refresh_from_db()
    family.refresh_from_db()
    assert image.series_id == children[0].pk
    assert document.series_id == children[0].pk
    assert image.image.name == 'retained/style.jpg'
    assert document.file.name == 'retained/catalog.pdf'
    assert image.is_visible is False
    assert document.is_visible is False
    assert family.presentation_photo_id == image.pk
    assert any(row['model'] == 'catalog.series' for row in report['backup'])
    again = cleanup(tmp_path, 'repeat.json', apply=True)
    assert again['changes'] == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    'dependency', ['color', 'project', 'published', 'video']
)
def test_cleanup_retains_parents_with_unresolved_dependencies(
    cleanup_series,
    tmp_path,
    dependency,
):
    parent, children = cleanup_series
    if dependency == 'color':
        origin = ColorGroup.objects.create(
            series=parent, name='RAL', any_ral=True
        )
        ColorGroup.objects.create(
            series=children[0],
            name='RAL',
            any_ral=True,
            legacy_origin=origin,
        )
    elif dependency == 'project':
        project = Project.objects.create(title='Проект')
        project.series.add(parent)
    elif dependency == 'published':
        Series.objects.filter(pk=parent.pk).update(is_published=True)
    else:
        Series.objects.filter(pk=parent.pk).update(video='retained/video.mp4')
    report = cleanup(tmp_path, 'backup.json', apply=True)
    assert Series.objects.filter(pk=parent.pk).exists()
    assert report['parents'][0]['status'] == 'retained'
    assert report['parents'][0]['blockers']
    if dependency == 'color':
        assert (
            ColorGroup.objects.get(legacy_origin=origin).legacy_origin_id
            == origin.pk
        )
    if dependency == 'project':
        assert project.series.filter(pk=parent.pk).exists()


@pytest.mark.django_db
def test_media_source_collision_retains_parent(cleanup_series, tmp_path):
    parent, children = cleanup_series
    for series in [parent, *children]:
        SeriesFile.objects.create(
            series=series,
            file='retained/same.pdf',
            title='Документ',
            source_url='https://example.org/file.pdf',
        )
    report = cleanup(tmp_path, 'backup.json', apply=True)
    assert Series.objects.filter(pk=parent.pk).exists()
    assert report['parents'][0]['status'] == 'retained'
    assert SeriesFile.objects.filter(series=parent).exists()


@pytest.mark.django_db
def test_nova_keeps_current_style_without_size_or_variant_and_all_variants(
    cleanup_series,
    tmp_path,
):
    parent, _ = cleanup_series
    nova = Series.objects.create(
        brand=parent.brand,
        category=parent.category,
        slug='nova-siluet',
        name='Nova Siluet',
    )
    variant = Variant.objects.create(
        series=nova,
        brand=parent.brand,
        article='NOVA-300',
        height_mm=300,
        width_mm=500,
        price=100,
    )
    photo = SeriesImage.objects.create(
        series=nova,
        image='retained/nova.jpg',
        image_width=1580,
        image_height=1160,
    )
    keep = Showcase.objects.create(
        series=nova,
        label='300 мм',
        variant=variant,
        position=0,
    )
    removed = Showcase.objects.create(
        series=nova,
        label='1800 мм',
        image='retained/second.jpg',
        image_width=1000,
        image_height=1000,
        position=1,
    )
    report = cleanup(tmp_path, 'backup.json', apply=True)
    keep = Showcase.objects.get(pk=keep.pk)
    assert nova.showcases.count() == 1
    assert keep.label == ''
    assert keep.variant_id is None
    assert keep.image.name == photo.image.name
    assert (keep.image_width, keep.image_height) == (1580, 1160)
    assert Variant.objects.filter(pk=variant.pk, height_mm=300).exists()
    assert SeriesImage.objects.filter(pk=photo.pk, series=nova).exists()
    assert any(
        row['model'] == 'catalog.showcase'
        and row['pk'] == removed.pk
        and row['fields']['image'] == 'retained/second.jpg'
        for row in report['backup']
    )
    assert cleanup(tmp_path, 'repeat.json', apply=True)['changes'] == 0


@pytest.mark.django_db
def test_apply_refuses_to_overwrite_backup_before_changing_rows(
    cleanup_series,
    tmp_path,
):
    parent, _ = cleanup_series
    path = tmp_path / 'backup.json'
    path.write_text('original backup')
    with pytest.raises(CommandError):
        call_command('cleanup_catalog_presentations', report=path, apply=True)
    assert path.read_text() == 'original backup'
    assert Series.objects.filter(pk=parent.pk).exists()


@pytest.mark.django_db
def test_report_does_not_acquire_row_locks(cleanup_series, tmp_path):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as queries:
        report = cleanup(tmp_path, 'read-only.json')
    assert report['parents'][0]['id'] == cleanup_series[0].pk
    assert not any('FOR UPDATE' in query['sql'] for query in queries)


@pytest.mark.django_db(transaction=True)
def test_cleanup_does_not_lock_unrelated_series_or_variant(cleanup_series):
    import psycopg
    from django.db import connections, transaction

    from apps.catalog.catalog_cleanup import lock_cleanup_rows

    parent, _ = cleanup_series
    unrelated = Series.objects.create(
        brand=parent.brand,
        category=parent.category,
        slug='unrelated-series',
        name='Другая серия',
    )
    variant = Variant.objects.create(series=unrelated, article='unrelated')
    other = psycopg.connect(
        **connections['default'].get_connection_params(), autocommit=True
    )
    try:
        with transaction.atomic():
            lock_cleanup_rows()
            with other.cursor() as cursor:
                cursor.execute(
                    'SELECT id FROM catalog_series WHERE id = %s '
                    'FOR UPDATE NOWAIT',
                    [unrelated.pk],
                )
                assert cursor.fetchone() == (unrelated.pk,)
                cursor.execute(
                    'SELECT id FROM catalog_variant WHERE id = %s '
                    'FOR UPDATE NOWAIT',
                    [variant.pk],
                )
                assert cursor.fetchone() == (variant.pk,)
    finally:
        other.close()
