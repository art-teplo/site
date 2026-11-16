import io
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.catalog.models import (
    Brand,
    Category,
    Color,
    ColorGroup,
    Series,
    SeriesImage,
    Showcase,
    Subcategory,
    Variant,
)
from apps.catalog.pricing import effective_percent, price_from
from apps.catalog.search import MAX_WORDS, words
from apps.content.models import Project


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / 'media'


def png(name='c.png'):
    buffer = io.BytesIO()
    Image.new('RGB', (4, 3)).save(buffer, 'PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), 'image/png')


def add_series(brand, category, slug, name, price, **fields):
    series = Series.objects.create(
        brand=brand,
        category=category,
        slug=slug,
        name=name,
        **fields,
    )
    Variant.objects.create(
        series=series,
        article=f'{slug}-1',
        height_mm=500,
        price_byn=Decimal(price),
    )
    return series


@pytest.fixture
def shop(db):  # noqa: ARG001
    brand = Brand.objects.create(slug='guardo', name='Guardo', note='n')
    category = Category.objects.create(
        slug='radiatory',
        name='Радиаторы',
        short='р',
        image=png(),
        image_alt='a',
    )
    tubular = Subcategory.objects.create(
        category=category,
        slug='trubchatye-t',
        name='Трубчатые',
        position=2,
    )
    alu = Subcategory.objects.create(
        category=category,
        slug='alyuminievye-t',
        name='Алюминиевые',
        position=1,
        image=png('t.png'),
        image_alt='алюминий',
    )
    Subcategory.objects.create(
        category=category,
        slug='skrytyj',
        name='Скрытый',
        is_published=False,
    )
    retta = add_series(
        brand,
        category,
        'retta',
        'Retta',
        '100',
        subcategory=tubular,
        position=1,
    )
    torre = add_series(
        brand,
        category,
        'torre',
        'Torre',
        '200',
        subcategory=tubular,
        position=2,
    )
    allumo = add_series(
        brand,
        category,
        'allumo',
        'Allumo',
        '50',
        subcategory=alu,
        position=3,
    )
    add_series(
        brand,
        category,
        'draft',
        'Черновик',
        '10',
        subcategory=tubular,
        is_published=False,
    )
    return SimpleNamespace(
        brand=brand,
        category=category,
        tubular=tubular,
        alu=alu,
        retta=retta,
        torre=torre,
        allumo=allumo,
    )


def slugs(data):
    return [card['series'] for card in data]


def test_categories_expose_published_types(client, shop):  # noqa: ARG001
    response = client.get(reverse('category-list'))
    types = response.json()[0]['types']
    assert [t['slug'] for t in types] == ['alyuminievye-t', 'trubchatye-t']
    assert types[0]['series_count'] == 1
    assert types[1]['series_count'] == 2
    assert types[1]['image'] is None
    assert types[0]['image']['alt'] == 'алюминий'
    assert set(types[0]['image']) == {'src', 'width', 'height', 'alt'}


def test_series_list_filters_by_type(client, shop):  # noqa: ARG001
    response = client.get(
        reverse('series-list'),
        {'category': 'radiatory', 'type': 'trubchatye-t'},
    )
    data = response.json()
    assert [c['series'] for c in data['results']] == ['retta', 'torre']
    assert {c['type'] for c in data['results']} == {'trubchatye-t'}


def test_card_type_is_null_without_subcategory(client, shop):
    Series.objects.filter(pk=shop.allumo.pk).update(subcategory=None)
    data = client.get(reverse('series-list')).json()['results']
    card = next(c for c in data if c['series'] == 'allumo')
    assert card['type'] is None


def test_hover_image_prefers_interior(client, shop):
    for kind, name in [('product', 'a'), ('product', 'b'), ('interior', 'i')]:
        SeriesImage.objects.create(
            series=shop.retta,
            image=png(f'{name}.png'),
            image_alt=name,
            kind=kind,
        )
    data = client.get(reverse('series-list')).json()['results']
    card = next(c for c in data if c['series'] == 'retta')
    assert card['image']['alt'] == 'a'
    assert card['hover_image']['alt'] == 'i'


def test_hover_image_falls_back_to_second_product(client, shop):
    for name in 'ab':
        SeriesImage.objects.create(
            series=shop.torre,
            image=png(f'{name}.png'),
            image_alt=name,
        )
    SeriesImage.objects.create(
        series=shop.allumo,
        image=png('x.png'),
        image_alt='x',
    )
    data = client.get(reverse('series-list')).json()['results']
    cards = {c['series']: c for c in data}
    assert cards['torre']['hover_image']['alt'] == 'b'
    assert cards['allumo']['hover_image'] is None
    assert cards['retta']['hover_image'] is None


def test_showcase_photos_follow_its_orientation(client, shop):
    """Вертикальная витрина: фото и наведение — только вертикальные или без
    ориентации, хотя горизонтальные стоят в админке раньше."""
    variant = Variant.objects.filter(series=shop.retta).first()
    Variant.objects.filter(pk=variant.pk).update(orientation='v')
    Showcase.objects.create(series=shop.retta, label='в', variant=variant)
    for kind, orientation, name in [
        ('product', 'h', 'ph'),
        ('product', 'v', 'pv'),
        ('interior', 'h', 'ih'),
        ('interior', '', 'i0'),
        ('interior', 'v', 'iv'),
    ]:
        SeriesImage.objects.create(
            series=shop.retta,
            image=png(f'{name}.png'),
            image_alt=name,
            kind=kind,
            orientation=orientation,
        )
    card = search(client, 'retta')[0]
    assert card['orientation'] == 'v'
    assert card['image']['alt'] == 'pv'
    # своя ориентация раньше фото без ориентации, горизонтальное — никогда
    assert card['hover_image']['alt'] == 'iv'


def test_detail_images_have_kind(client, shop):
    SeriesImage.objects.create(
        series=shop.retta,
        image=png(),
        image_alt='i',
        kind='interior',
    )
    data = client.get(reverse('series-detail', args=['retta'])).json()
    assert data['images'][0]['kind'] == 'interior'


def test_similar_same_type_first_and_without_self(client, shop):  # noqa: ARG001
    data = client.get(reverse('series-detail', args=['retta'])).json()
    assert slugs(data['similar']) == ['torre', 'allumo']
    data = client.get(reverse('series-detail', args=['allumo'])).json()
    assert slugs(data['similar']) == ['retta', 'torre']
    assert 'hover_image' in data['similar'][0]


def test_similar_limited_to_eight(client, shop):
    for i in range(10):
        add_series(
            shop.brand,
            shop.category,
            f's{i}',
            f'S{i}',
            '70',
            subcategory=shop.tubular,
        )
    data = client.get(reverse('series-detail', args=['retta'])).json()
    assert len(data['similar']) == 4


def test_similar_ignores_other_categories(client, shop):
    other = Category.objects.create(
        slug='konvektory',
        name='Конвекторы',
        short='к',
        image=png(),
        image_alt='a',
    )
    add_series(shop.brand, other, 'conv', 'Conv', '10')
    data = client.get(reverse('series-detail', args=['retta'])).json()
    assert 'conv' not in slugs(data['similar'])


def test_detail_projects(client, shop):
    shown = Project.objects.create(
        slug='flat-1',
        title='Квартира',
        place='Минск',
        image=png(),
        image_alt='p',
    )
    shown.series.add(shop.retta)
    hidden = Project.objects.create(
        slug='flat-2',
        title='Скрытый',
        place='Минск',
        image=png('h.png'),
        image_alt='h',
        is_published=False,
    )
    hidden.series.add(shop.retta)
    other = Project.objects.create(
        slug='flat-3',
        title='Чужой',
        place='Минск',
        image=png('o.png'),
        image_alt='o',
    )
    other.series.add(shop.torre)
    data = client.get(reverse('series-detail', args=['retta'])).json()
    assert len(data['projects']) == 1
    project = data['projects'][0]
    assert project['slug'] == 'flat-1'
    assert 'kind' not in project
    assert {'title', 'place', 'image', 'photos', 'video_url'} <= set(project)
    assert (
        client.get(
            reverse('series-detail', args=['allumo']),
        ).json()['projects']
        == []
    )


def search(client, q):
    response = client.get(reverse('search'), {'q': q})
    assert response.status_code == 200
    return response.json()


def test_search_short_query_is_empty(client, shop):  # noqa: ARG001
    assert search(client, 'r') == []
    assert search(client, ' ') == []
    assert client.get(reverse('search')).json() == []


def test_search_by_name_brand_type_category(client, shop):  # noqa: ARG001
    assert slugs(search(client, 'RETTA')) == ['retta']
    assert slugs(search(client, 'guardo')) == ['retta', 'torre', 'allumo']
    assert slugs(search(client, 'алюмин')) == ['allumo']
    assert slugs(search(client, 'радиатор')) == ['retta', 'torre', 'allumo']
    assert search(client, 'черновик') == []


def test_search_exact_article(client, shop):  # noqa: ARG001
    assert slugs(search(client, 'torre-1')) == ['torre']
    assert search(client, 'torre-') == []


def test_search_limited_to_twenty(client, shop):
    for i in range(25):
        add_series(shop.brand, shop.category, f'm{i}', f'Many {i}', '10')
    assert len(search(client, 'many')) == 20


def test_search_every_word_in_any_field(client, shop):  # noqa: ARG001
    # Бренд и название — в разных полях: целиком строки нет нигде
    assert slugs(search(client, 'guardo retta')) == ['retta']
    assert search(client, 'guardo черновик') == []


def test_search_words_deduplicated_and_capped():
    # Длинный запрос из коротких слов не размножает подзапросы к базе
    assert words('ab ab cd') == ['ab', 'cd']
    assert len(words(' '.join(f'w{i}' for i in range(30)))) == MAX_WORDS


def test_search_long_query_still_finds(client, shop):  # noqa: ARG001
    assert slugs(search(client, 'guardo retta ' * 10)) == ['retta']


def test_search_keyboard_layout_synonyms_translit(client, shop):  # noqa: ARG001
    everything = ['retta', 'torre', 'allumo']
    assert slugs(search(client, 'udfhlj')) == everything  # «гуардо» в EN
    assert slugs(search(client, 'гуардо')) == everything
    assert slugs(search(client, 'куееф')) == ['retta']  # «retta» в RU
    assert slugs(search(client, 'гуардо ретта')) == ['retta']
    assert slugs(search(client, 'батареи')) == everything


def test_search_sort_and_limit(client, shop):  # noqa: ARG001
    url = reverse('search')

    def found(**params):
        response = client.get(url, {'q': 'guardo', **params})
        return slugs(response.json())

    assert found(sort='price') == ['allumo', 'retta', 'torre']
    assert found(sort='-price') == ['torre', 'retta', 'allumo']
    assert found(sort='bogus') == ['retta', 'torre', 'allumo']
    assert found(limit='1') == ['retta']
    assert len(found(limit='nope')) == 3
    assert len(found(limit='0')) == 1


def test_card_prefers_photo_shaped_like_card(client, shop):
    """Рамка карточки 4:3: вертикальное товарное фото, даже первое в
    админке, уступает горизонтальному."""
    wide = SeriesImage.objects.create(
        series=shop.retta,
        image=png('wide.png'),
        image_alt='w',
        kind=SeriesImage.Kind.PRODUCT,
        position=3,
    )
    tall = SeriesImage.objects.create(
        series=shop.retta,
        image=png('tall.png'),
        image_alt='t',
        kind=SeriesImage.Kind.PRODUCT,
        position=2,
    )
    SeriesImage.objects.filter(pk=wide.pk).update(
        image_width=1600,
        image_height=1000,
    )
    SeriesImage.objects.filter(pk=tall.pk).update(
        image_width=1000,
        image_height=1300,
    )
    card = search(client, 'retta')[0]
    assert card['image']['alt'] == 'w'


def test_card_takes_first_fitting_photo_in_admin_order(client, shop):
    """Из фото, которые ложатся в рамку 4:3 без размытого фона, — первое по
    порядку админки: менеджер выбирает фото карточки перетаскиванием."""
    for position, (name, width, height) in enumerate(
        [('tall', 1000, 1300), ('first', 1600, 1000), ('exact', 1600, 1200)],
    ):
        image = SeriesImage.objects.create(
            series=shop.retta,
            image=png(f'{name}.png'),
            image_alt=name,
            kind=SeriesImage.Kind.PRODUCT,
            position=position,
        )
        SeriesImage.objects.filter(pk=image.pk).update(
            image_width=width,
            image_height=height,
        )
    assert search(client, 'retta')[0]['image']['alt'] == 'first'


def test_scheme_never_becomes_card_or_hover_photo(client, shop):
    """Схема подключений — не фото товара: даже первой в админке она не
    идёт ни в карточку, ни на наведение — без товарных фото карточка берёт
    интерьерное."""
    for position, (name, kind) in enumerate(
        [
            ('scheme', SeriesImage.Kind.SCHEME),
            ('interior', SeriesImage.Kind.INTERIOR),
        ],
    ):
        SeriesImage.objects.create(
            series=shop.retta,
            image=png(f'{name}.png'),
            image_alt=name,
            kind=kind,
            position=position,
        )
    found = search(client, 'retta')[0]
    assert found['image']['alt'] == 'interior'
    assert found['hover_image'] is None


def test_image_focus_in_api_only_when_moved(client, shop):  # noqa: ARG001
    alu = Subcategory.objects.get(slug='alyuminievye-t')
    alu.image_focus = '30 70'
    alu.save()
    types = client.get(reverse('category-list')).json()[0]['types']
    assert types[0]['image']['focus'] == {'x': 30, 'y': 70}


def test_water_heating_facet_label_is_russian(client, shop):
    category = Category.objects.create(
        slug='polotentsesushiteli',
        name='Полотенцесушители',
        short='п',
        image=png(),
        image_alt='a',
    )
    series = add_series(shop.brand, category, 'alto', 'Alto', '10')
    Variant.objects.filter(series=series).update(
        attrs={'heating': 'electric'},
    )
    add_series(shop.brand, category, 'alto2', 'Alto2', '10')
    Variant.objects.filter(series__slug='alto2').update(
        attrs={'heating': 'water'},
    )
    data = client.get(
        reverse('series-list'),
        {'category': 'polotentsesushiteli'},
    ).json()
    heating = next(f for f in data['facets'] if f['key'] == 'heating')
    assert {v['value']: v['label'] for v in heating['values']} == {
        'water': 'водяной',
        'electric': 'электрический',
    }


def test_empty_facets_are_dropped(client, shop):  # noqa: ARG001
    data = client.get(
        reverse('series-list'),
        {'category': 'radiatory'},
    ).json()
    keys = {f['key'] for f in data['facets']}
    # у всех вариантов одна высота, нет цветов, подключений и т. п.
    assert 'height' not in keys
    assert 'color' not in keys
    assert 'connection' not in keys
    assert 'price' in keys


def test_effective_percent():
    def group(value):
        return SimpleNamespace(percent=Decimal(value))

    assert effective_percent(group('0')) == 0
    assert effective_percent(group('-15')) == 0
    assert effective_percent(group('-0.5')) == 0
    assert effective_percent(group('5')) == 5
    assert effective_percent(group('5.01')) == 6
    assert effective_percent(group('7.5')) == 8


def test_color_percent_is_whole_and_never_discounts(client, shop):
    base = ColorGroup.objects.create(
        series=shop.retta,
        name='База',
        is_base=True,
    )
    cheaper = ColorGroup.objects.create(
        series=shop.retta,
        name='Скидка',
        percent=Decimal('-10'),
    )
    fraction = ColorGroup.objects.create(
        series=shop.retta,
        name='Дробный',
        percent=Decimal('2.5'),
    )
    ral = Color.objects.create(code='RAL 1', name='1', hex='#111111')
    cheaper.colors.add(ral)
    data = client.get(reverse('series-detail', args=['retta'])).json()
    percents = {g['name']: g['percent'] for g in data['color_groups']}
    assert percents == {'База': 0, 'Скидка': 0, 'Дробный': 3}
    assert all(isinstance(p, int) for p in percents.values())
    assert data['price_from_by_group'][str(cheaper.pk)] == 100
    assert data['price_from_by_group'][str(fraction.pk)] == 103
    assert data['price_from'] == 100
    assert price_from([(Decimal(100), [cheaper])]) == 100
    assert base.is_base


@pytest.mark.parametrize(
    ('sort', 'expected'),
    [
        (None, ['retta', 'torre', 'allumo']),
        ('price', ['allumo', 'retta', 'torre']),
        ('-price', ['torre', 'retta', 'allumo']),
        ('name', ['retta', 'torre', 'allumo']),
    ],
)
def test_series_list_sort(client, shop, sort, expected):  # noqa: ARG001
    params = {'category': 'radiatory'} | ({'sort': sort} if sort else {})
    response = client.get(reverse('series-list'), params)
    assert slugs(response.json()['results']) == expected


def test_variant_row_has_base_price_for_client_repricing(client, shop):
    response = client.get(reverse('series-variants', args=[shop.retta.slug]))
    row = response.json()['results'][0]
    assert row['price_byn'] == 100.0
    assert row['color_groups'] == []


@pytest.mark.parametrize(
    ('orientation', 'height', 'expected'),
    [
        ('h', 2000, 'h'),
        ('', 300, 'h'),
        ('', 1800, 'v'),
        ('', None, ''),
    ],
)
def test_showcase_orientation_falls_back_to_height(
    orientation,
    height,
    expected,
):
    from apps.catalog.serializers import _orientation  # noqa: PLC0415

    variant = SimpleNamespace(
        orientation=orientation,
        height_mm=height,
        width_mm=200,
    )
    assert _orientation(variant) == expected
