import pytest

from apps.catalog.archive_transfer import transfer_archive
from apps.catalog.models import (
    Brand,
    Category,
    Color,
    ColorGroup,
    ProductFamily,
    Series,
    SeriesFile,
    SeriesImage,
    Variant,
)
from apps.catalog.views import _legacy_color


@pytest.mark.django_db
def test_archive_transfer_keeps_old_color_links_and_routes_materials():
    brand = Brand.objects.create(slug='kzto', name='КЗТО')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    slug = 'kzto-quadrum-neo-50'
    parent = Series.objects.create(
        slug=slug,
        name='Quadrum',
        brand=brand,
        category=category,
        video='video.mp4',
        is_published=False,
    )
    horizontal, vertical = [
        Series.objects.create(
            slug=f'{slug}-{orientation}',
            name=f'Quadrum {orientation}',
            brand=brand,
            category=category,
            is_published=True,
            factory_orientation=orientation,
        )
        for orientation in ('h', 'v')
    ]
    for child in (horizontal, vertical):
        Variant.objects.create(series=child, article=child.slug)
    original = ColorGroup.objects.create(
        series=parent, name='RAL', any_ral=True
    )
    color = Color.objects.create(code='RAL 9005', name='Чёрный', hex='#000000')
    original.colors.add(color)
    existing = ColorGroup.objects.create(
        series=horizontal,
        name='RAL для H',
        any_ral=True,
        legacy_origin=original,
    )
    photo = SeriesImage.objects.create(
        series=parent,
        image='style.jpg',
        image_width=320,
        image_height=240,
        kind=SeriesImage.Kind.INTERIOR,
    )
    gallery_photo = SeriesImage.objects.create(
        series=parent,
        image='render.jpg',
        image_width=320,
        image_height=240,
        source_url='https://kztoradiator.ru/assets/manager/catalog/qneo50h-2.png',
    )
    family = ProductFamily.objects.create(
        key='quadrum',
        name='Quadrum',
        brand=brand,
        category=category,
        presentation_photo=photo,
    )
    SeriesFile.objects.create(
        series=parent, file='manual.pdf', title='Паспорт 50V'
    )

    transfer_archive(parent)
    assert not Series.objects.filter(slug=slug).exists()
    existing.refresh_from_db()
    assert existing.legacy_origin_id is None
    assert (
        _legacy_color(slug, horizontal, f'any-{original.pk}')
        == f'any-{existing.pk}'
    )
    assert vertical.color_groups.get().colors.get() == color
    assert not horizontal.files.exists()
    assert vertical.files.get().file.name == 'manual.pdf'
    family.refresh_from_db()
    assert family.presentation_photo.image.name == 'style.jpg'
    assert list(
        horizontal.images.filter(is_visible=True).values_list(
            'image', flat=True
        )
    ) == [gallery_photo.image.name]
    assert not vertical.images.filter(is_visible=True).exists()
    for child in (horizontal, vertical):
        child.refresh_from_db()
        assert child.video.name == 'video.mp4'
