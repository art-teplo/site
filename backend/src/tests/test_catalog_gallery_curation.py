import pytest

from apps.catalog import serializers
from apps.catalog.models import Brand, Category, Series, SeriesImage


@pytest.mark.django_db
def test_hidden_photos_do_not_appear_in_gallery_or_cards():
    brand = Brand.objects.create(slug='kzto', name='КЗТО')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    series = Series.objects.create(
        slug='test', name='Test', brand=brand, category=category
    )
    hidden = SeriesImage.objects.create(
        series=series, position=0, is_visible=False
    )
    shown = SeriesImage.objects.create(
        series=series,
        position=1,
        image='catalog/shown.jpg',
        image_width=100,
        image_height=100,
    )
    assert serializers._photos(series) == [shown]  # noqa: SLF001
    detail = serializers.series_detail(
        series,
        ranges={},
        range_steps={},
        price_from=None,
        price_from_by_group={},
        executions=[],
        columns=[],
        filters=[],
        similar=[],
        projects=[],
    )
    assert len(detail['images']) == 1
    assert hidden.pk != shown.pk
