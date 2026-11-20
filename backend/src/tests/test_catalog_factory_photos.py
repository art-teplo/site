import io
from unittest.mock import patch

import pytest
from django.db.models.fields.files import ImageFieldFile
from PIL import Image

from apps.catalog.importers import factory_files, factory_photos
from apps.catalog.importers.factory_photos import (
    Summary,
    guardo_renders,
    import_series,
    prepare,
)
from apps.catalog.models import Brand, Category, Color, Series, SeriesImage

BASE = 'https://guardo.ru/catalog/retta/'


def render(height, position):
    return (
        f'/upload/resize_cache/iblock/abc/1400_932_hash/'
        f'guardo-retta-{height}-mm-vysotoy-{position}-polozhenie.jpg'
    )


def page(*paths):
    return ' '.join(f'srcset="/x.jpg 1x,{p} 2x"' for p in paths)


def jpeg(size=(30, 20)):
    out = io.BytesIO()
    Image.new('RGB', size, (90, 90, 90)).save(out, 'JPEG')
    return out.getvalue()


def test_renders_two_heights_per_position_closest_to_typical():
    html = page(
        render(300, 'vertikalnoe'),
        render(1200, 'vertikalnoe'),
        render(1500, 'vertikalnoe'),
        render(1800, 'vertikalnoe'),
        render(230, 'gorizontalnoe'),
        render(430, 'gorizontalnoe'),
        render(580, 'gorizontalnoe'),
    )
    chosen = [(p.orientation, p.height_mm) for p in guardo_renders(html, BASE)]
    assert chosen == [('v', 1800), ('v', 1200), ('h', 430), ('h', 230)]


def test_render_without_position_in_name_goes_by_height():
    # Pilon: «…-pilon-1800-mm-vysotoy-belye.jpg» — положения в имени нет
    html = page(
        '/upload/resize_cache/iblock/a/1400_932_h/pilon-1800-mm-vysotoy-belye.jpg',
        '/upload/resize_cache/iblock/a/1400_932_h/pilon-450-mm-vysotoy-belye.jpg',
    )
    chosen = [(p.orientation, p.height_mm) for p in guardo_renders(html, BASE)]
    assert chosen == [('v', 1800), ('h', 450)]


def test_big_png_becomes_jpeg_within_max_side():
    out = io.BytesIO()
    Image.new('RGB', (3000, 1500)).save(out, 'PNG')
    data, ext, width, height = prepare(out.getvalue())
    assert (ext, width, height) == ('jpg', 2000, 1000)
    with Image.open(io.BytesIO(data)) as image:
        assert image.format == 'JPEG'


@pytest.mark.django_db
def test_import_puts_new_photos_first_and_skips_repeats():
    brand = Brand.objects.create(name='Guardo', slug='guardo')
    category = Category.objects.create(name='К', slug='k')
    series = Series.objects.create(
        brand=brand,
        category=category,
        name='Guardo Retta 3P',
        slug='guardo-retta-3p',
    )
    old = SeriesImage.objects.create(
        series=series,
        image_alt='старое',
        position=0,
    )
    html = page(render(1800, 'vertikalnoe'), render(430, 'gorizontalnoe'))

    def fetch(url):
        return html.encode() if url.endswith('/') else jpeg()

    # Как S3: при записи файла ImageField не может прочитать размеры
    no_width = patch.object(ImageFieldFile, 'width', property(lambda _: None))
    no_height = patch.object(
        ImageFieldFile, 'height', property(lambda _: None)
    )
    with patch.object(factory_photos, 'fetch', fetch), no_width, no_height:
        summary = Summary()
        import_series(series, summary, dry_run=False)
        again = Summary()
        import_series(series, again, dry_run=False)

    images = list(series.images.all())
    assert [(i.image_alt, i.position) for i in images] == [
        ('Guardo Retta 3P, 1800 мм, вертикальный', 0),
        ('Guardo Retta 3P, 430 мм, горизонтальный', 1),
        ('старое', 2),
    ]
    assert images[0].kind == SeriesImage.Kind.PRODUCT
    # Размеры — в базе, а не дочитаны из файла при загрузке записи
    stored = SeriesImage.objects.filter(pk=images[0].pk)
    assert list(stored.values_list('image_width', 'image_height')) == [
        (30, 20)
    ]
    assert (summary.added, again.added, again.skipped) == (2, 0, 2)
    old.refresh_from_db()
    assert old.position == 2


@pytest.mark.django_db
def test_import_targets_split_series_even_when_archive_is_absent(
    monkeypatch, settings, tmp_path
):
    from django.core.management import call_command  # noqa: PLC0415

    settings.MEDIA_ROOT = tmp_path
    brand = Brand.objects.create(name='Guardo', slug='guardo')
    category = Category.objects.create(name='К', slug='k')
    horizontal = Series.objects.create(
        brand=brand,
        category=category,
        name='Guardo Retta 3P H',
        slug='guardo-retta-3p-h',
        factory_orientation='h',
    )
    html = page(
        render(1800, 'vertikalnoe'),
        render(430, 'gorizontalnoe'),
        render(250, 'beloe'),
    )

    def fetch(url):
        return html.encode() if url.endswith('/') else jpeg()

    monkeypatch.setattr(factory_photos, 'fetch', fetch)
    call_command('import_photos', brand='guardo')
    photo = horizontal.images.get()
    assert '430 мм' in photo.image_alt


@pytest.mark.parametrize(
    ('name', 'expected'),
    [
        ('3P-1800 6 NK-VER-L black 02.jpg', ('v', 'RAL 9005', 'product')),
        ('3P-NK-GOR_L-480-bej-01.jpg', ('h', 'RAL 1015', 'product')),
        ('3p-2200-r9016-NK-VER-R.jpg', ('v', 'RAL 9016', 'product')),
        (
            'guardo-torre-4d-8-sections-1000-vertical-7040-website.jpg',
            ('v', 'RAL 7040', 'product'),
        ),
        ('connection-gurdo-retta-gor.jpg', ('h', '', 'scheme')),
        ('3P 500 8 NK-VER-R grey-02-zoom.jpg', None),  # крупный план
        ('guardo-pilon-01.jpg', None),  # ни цвета, ни положения
    ],
)
def test_guardo_picture_from_file_name(name, expected):
    photo = factory_photos.guardo_picture(f'https://guardo.ru/x/{name}')
    if expected is None:
        assert photo is None
        return
    assert (photo.orientation, photo.color, photo.kind) == expected
    assert photo.last


def test_guardo_extras_one_render_per_color_and_schemes_last():
    base = 'trubchatye-radiatory-guardo-retta-3p/'
    item = f'/catalog/{base}h1800/'
    pictures = [
        'connection-gurdo-retta-ver.jpg',
        '3P-1800 8 NK-VER-R white 02-mirror.jpg',
        '3P-1800 8 NK-VER-R white 01.jpg',  # не отзеркаленный — лучше
        '3P-1800 6 NK-VER-L black 02.jpg',
        '3P-NK-GOR-L-480-white-01.jpg',
    ]
    pages = {
        'https://guardo.ru' + item: ' '.join(
            f'data-src="/upload/resize_cache/iblock/a/1440_960_1/{p}"'
            for p in pictures
        ),
    }
    with patch.object(
        factory_photos, 'fetch', lambda url: pages[url].encode()
    ):
        photos = factory_photos.guardo_extras(
            f'<a class="x" href="{item}">',
            base,
            Summary(),
        )
    assert [(p.orientation, p.color, p.kind) for p in photos] == [
        ('v', 'RAL 9016', 'product'),
        ('v', 'RAL 9005', 'product'),
        ('h', 'RAL 9016', 'product'),
        ('v', '', 'scheme'),
    ]
    assert 'mirror' not in photos[0].url


def test_velar_photos_product_first_with_colors():
    photos = factory_photos.velar_photos('velar-p30')
    kinds = [p.kind for p in photos]
    assert kinds[:2] == ['product', 'product']
    assert set(kinds[2:]) == {'interior'}
    assert [p.orientation for p in photos[:2]] == ['v', 'h']
    colors = {p.label: p.color for p in photos if p.label}
    assert colors == {'белый': 'RAL 9016', 'чёрный': 'RAL 9005', 'красный': ''}


@pytest.mark.django_db
def test_last_photos_go_to_gallery_end_with_color():
    brand = Brand.objects.create(name='Guardo', slug='guardo')
    category = Category.objects.create(name='К', slug='k')
    series = Series.objects.create(
        brand=brand,
        category=category,
        name='Guardo Retta 3P',
        slug='guardo-retta-3p',
    )
    black = Color.objects.create(code='RAL 9005', name='Чёрный', hex='#000')
    SeriesImage.objects.create(series=series, image_alt='старое', position=0)
    photos = [
        factory_photos.Photo('https://x/a.jpg', 'v'),
        factory_photos.Photo(
            'https://x/b.jpg',
            'v',
            color='RAL 9005',
            label='RAL 9005',
            last=True,
        ),
        factory_photos.Photo(
            'https://x/c.jpg',
            'h',
            kind=SeriesImage.Kind.SCHEME,
            last=True,
        ),
    ]
    with (
        patch.object(factory_photos, 'photos_for', lambda *_: photos),
        patch.object(factory_photos, 'fetch', lambda _: jpeg()),
    ):
        import_series(series, Summary(), dry_run=False)
    images = list(series.images.order_by('position'))
    assert [(i.image_alt, i.kind, i.color) for i in images] == [
        ('Guardo Retta 3P, вертикальный', 'product', None),
        ('старое', 'product', None),
        ('Guardo Retta 3P, вертикальный, RAL 9005', 'product', black),
        (
            'Guardo Retta 3P, горизонтальный, схема подключений',
            'scheme',
            None,
        ),
    ]


@pytest.mark.django_db
def test_factory_pdf_uploaded_once_for_all_series():
    brand = Brand.objects.create(name='Guardo', slug='guardo')
    category = Category.objects.create(name='К', slug='k')
    retta = [
        Series.objects.create(
            brand=brand,
            category=category,
            name=slug,
            slug=slug,
        )
        for slug in ('guardo-retta-3p', 'guardo-retta-4p')
    ]
    calls = []

    def fetch(url):
        calls.append(url)
        return b'%PDF-1.4 test'

    summary = factory_files.Summary()
    with patch.object(factory_files, 'fetch', fetch):
        for series in retta:
            factory_files.import_series(series, summary, dry_run=False)
        again = factory_files.Summary()
        factory_files.import_series(retta[0], again, dry_run=False)

    assert len(calls) == 2  # каталог и паспорт — по разу на обе серии
    first, second = (list(s.files.values_list('title', 'file')) for s in retta)
    assert [t for t, _ in first] == [
        'Каталог Guardo Retta',
        'Паспорт Guardo Retta',
    ]
    assert first == second  # тот же файл в хранилище
    assert (summary.added, again.added, again.skipped) == (4, 0, 2)
