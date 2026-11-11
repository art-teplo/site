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
    Variant,
)

URL = reverse('series-list')


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / 'media'


def png():
    buffer = io.BytesIO()
    Image.new('RGB', (4, 3)).save(buffer, 'PNG')
    return SimpleUploadedFile('c.png', buffer.getvalue(), 'image/png')


def make_variant(series, article, **fields):
    return Variant.objects.create(series=series, article=article, **fields)


@pytest.fixture
def catalog(db):  # noqa: ARG001
    """КЗТО «Гармония А40»: высоты 334 и 1284, подключения side и
    bottom_left, две витрины и две группы цветов; Guardo «Retta» без
    витрин и фото; неопубликованная серия КЗТО."""
    kzto = Brand.objects.create(slug='kzto', name='КЗТО', note='n')
    guardo = Brand.objects.create(slug='guardo', name='Guardo', note='n')
    radiatory = Category.objects.create(
        slug='radiatory',
        name='Радиаторы',
        short='р',
        image=png(),
        image_alt='a',
    )
    garmoniya = Series.objects.create(
        brand=kzto,
        category=radiatory,
        slug='garmoniya-a40',
        name='Гармония А40',
        position=1,
    )
    ral9016 = Color.objects.create(
        code='RAL 9016',
        name='Белый',
        hex='#f6f6f6',
    )
    ral9005 = Color.objects.create(
        code='RAL 9005',
        name='Чёрный',
        hex='#0a0a0a',
    )
    standard = ColorGroup.objects.create(
        series=garmoniya,
        name='Стандартные',
        percent=0,
        is_base=True,
        position=1,
    )
    standard.colors.add(ral9016)
    black = ColorGroup.objects.create(
        series=garmoniya,
        name='Чёрный',
        percent=Decimal('10'),
        position=2,
    )
    black.colors.add(ral9005)
    low_side = make_variant(
        garmoniya,
        'GA-334-S',
        height_mm=334,
        width_mm=500,
        power_w=400,
        tubes=2,
        connection='side',
        orientation='h',
        price_byn=Decimal('100.50'),
    )
    low_bottom = make_variant(
        garmoniya,
        'GA-334-B',
        height_mm=334,
        width_mm=500,
        power_w=420,
        tubes=2,
        connection='bottom_left',
        orientation='h',
        price_byn=Decimal('120.00'),
    )
    tall_side = make_variant(
        garmoniya,
        'GA-1284-S',
        height_mm=1284,
        width_mm=500,
        power_w=1200,
        tubes=2,
        connection='side',
        orientation='v',
        price_byn=Decimal('300.00'),
    )
    tall_bottom = make_variant(
        garmoniya,
        'GA-1284-B',
        height_mm=1284,
        width_mm=500,
        power_w=1250,
        tubes=2,
        connection='bottom_left',
        orientation='v',
        price_byn=Decimal('320.00'),
    )
    Showcase.objects.create(
        series=garmoniya,
        label='334 мм',
        variant=low_side,
        position=1,
    )
    Showcase.objects.create(
        series=garmoniya,
        label='1284 мм, вертикальный',
        variant=tall_side,
        position=2,
    )
    retta = Series.objects.create(
        brand=guardo,
        category=radiatory,
        slug='retta',
        name='Retta',
        position=2,
    )
    retta_a = make_variant(
        retta,
        'R-500-A',
        height_mm=500,
        power_w=800,
        connection='diagonal',
        price_byn=Decimal('210.00'),
    )
    retta_b = make_variant(
        retta,
        'R-500-B',
        height_mm=500,
        power_w=900,
        connection='diagonal',
        price_byn=Decimal('190.00'),
    )
    hidden = Series.objects.create(
        brand=kzto,
        category=radiatory,
        slug='hidden',
        name='Скрытая',
        is_published=False,
    )
    make_variant(hidden, 'H-1', height_mm=300, price_byn=Decimal('50'))
    return SimpleNamespace(
        kzto=kzto,
        guardo=guardo,
        category=radiatory,
        garmoniya=garmoniya,
        retta=retta,
        hidden=hidden,
        ral9016=ral9016,
        ral9005=ral9005,
        standard=standard,
        black=black,
        variants=SimpleNamespace(
            low_side=low_side,
            low_bottom=low_bottom,
            tall_side=tall_side,
            tall_bottom=tall_bottom,
            retta_a=retta_a,
            retta_b=retta_b,
        ),
    )


def fetch(client, **params):
    response = client.get(URL, {'category': 'radiatory', **params})
    assert response.status_code == 200
    return response.json()


def facet(data, key):
    return next(f for f in data['facets'] if f['key'] == key)


def test_series_list_one_card_per_showcase(client, catalog):  # noqa: ARG001
    data = fetch(client, brand='kzto')
    assert data['count'] == 2
    first, second = data['results']
    assert first == {
        'series': 'garmoniya-a40',
        'name': 'Гармония А40',
        'brand': 'kzto',
        'label': '334 мм',
        'height_mm': 334,
        'price_from': 101,
        'image': None,
        'colors': [
            {'code': 'RAL 9016', 'name': 'Белый', 'hex': '#f6f6f6'},
            {'code': 'RAL 9005', 'name': 'Чёрный', 'hex': '#0a0a0a'},
        ],
    }
    assert second['label'] == '1284 мм, вертикальный'
    assert second['height_mm'] == 1284
    assert second['price_from'] == 300


def test_series_without_showcase_and_photo_still_listed(client, catalog):  # noqa: ARG001
    data = fetch(client, brand='guardo')
    assert data['count'] == 1
    card = data['results'][0]
    assert card['label'] == ''
    assert card['image'] is None
    assert card['price_from'] == 190
    assert card['colors'] == []


def test_card_image_falls_back_to_first_series_photo(client, catalog):
    SeriesImage.objects.create(
        series=catalog.garmoniya,
        image=png(),
        image_alt='общее',
    )
    cards = fetch(client, brand='kzto')['results']
    assert {c['image']['alt'] for c in cards} == {'общее'}
    own = Showcase.objects.get(label='334 мм')
    own.image = png()
    own.save()
    # Своё фото витрины важнее
    cards = fetch(client, brand='kzto')['results']
    assert cards[0]['image']['src'].startswith('/media/catalog_showcase/')
    assert cards[1]['image']['alt'] == 'общее'


def test_filter_height_hides_other_showcases(client, catalog):  # noqa: ARG001
    data = fetch(client, height_min='1000')
    assert [c['label'] for c in data['results']] == ['1284 мм, вертикальный']
    assert data['count'] == 1


def test_price_from_uses_matching_variants_only(client, catalog):  # noqa: ARG001
    data = fetch(client, brand='kzto', connection='bottom_left')
    assert [(c['label'], c['price_from']) for c in data['results']] == [
        ('334 мм', 120),
        ('1284 мм, вертикальный', 320),
    ]


def test_price_rounds_half_up(client, catalog):  # noqa: ARG001
    Variant.objects.filter(article='R-500-B').update(
        price_byn=Decimal('190.50'),
    )
    Variant.objects.filter(article='R-500-A').update(
        price_byn=Decimal('300'),
    )
    assert fetch(client, brand='guardo')['results'][0]['price_from'] == 191


def test_facet_counts_ignore_own_filter(client, catalog):  # noqa: ARG001
    data = fetch(client, connection='side')
    values = {v['value']: v for v in facet(data, 'connection')['values']}
    assert values['side']['count'] == 2
    assert values['side']['label'] == 'боковое'
    assert values['bottom_left']['count'] == 2
    assert values['diagonal']['count'] == 2
    # Чужие фильтры считаются: высота сужает счётчик
    data = fetch(client, connection='side', height_min='1000')
    values = {
        v['value']: v['count'] for v in facet(data, 'connection')['values']
    }
    assert values == {'side': 1, 'bottom_left': 1}


def test_range_facets_cover_whole_category(client, catalog):  # noqa: ARG001
    data = fetch(client, height_min='1000')
    height = facet(data, 'height')
    assert (height['min'], height['max'], height['unit']) == (334, 1284, 'мм')
    area = facet(data, 'area')
    assert (area['min'], area['max']) == (4, 12.5)
    price = facet(data, 'price')
    assert (price['min'], price['max']) == (100, 320)


def test_area_filter_is_power_over_100(client, catalog):  # noqa: ARG001
    data = fetch(client, area_min='11')
    assert [c['label'] for c in data['results']] == ['1284 мм, вертикальный']
    assert fetch(client, area_max='3')['count'] == 0


def test_brand_facet_has_names(client, catalog):  # noqa: ARG001
    values = facet(fetch(client), 'brand')['values']
    assert values == [
        {'value': 'guardo', 'label': 'Guardo', 'count': 2},
        {'value': 'kzto', 'label': 'КЗТО', 'count': 4},
    ]


def test_color_filter_inherits_series_groups(client, catalog):  # noqa: ARG001
    data = fetch(client, color='RAL 9005')
    assert {c['series'] for c in data['results']} == {'garmoniya-a40'}
    colors = facet(data, 'color')['values']
    assert {c['value']: c['count'] for c in colors} == {
        'RAL 9016': 4,
        'RAL 9005': 4,
    }
    assert colors[0]['hex']


def test_color_filter_respects_explicit_variant_groups(client, catalog):
    # Вариант с явным списком групп доступен только в них
    catalog.variants.tall_side.color_groups.add(catalog.standard)
    catalog.variants.tall_bottom.color_groups.add(catalog.black)

    def labels(**params):
        data = fetch(client, brand='kzto', color='RAL 9005', **params)
        return [c['label'] for c in data['results']]

    # tall_side чёрным недоступен: по боковому подключению высоких нет
    assert labels(height_min='1000', connection='side') == []
    # tall_bottom доступен
    assert labels(height_min='1000', connection='bottom_left') == [
        '1284 мм, вертикальный'
    ]
    # Низкие без явных групп наследуют группы серии
    assert labels(height_max='400', connection='side') == ['334 мм']
    black = next(
        v
        for v in facet(fetch(client), 'color')['values']
        if v['value'] == 'RAL 9005'
    )
    assert black['count'] == 3


def test_execution_skipped_in_own_facets(client, catalog):  # noqa: ARG001
    data = fetch(client, execution='2-side')
    values = {v['value'] for v in facet(data, 'connection')['values']}
    assert values == {'side', 'bottom_left', 'diagonal'}


def test_unknown_color_ignored(client, catalog):  # noqa: ARG001
    assert fetch(client, color='RAL 0000')['count'] == fetch(client)['count']


def test_execution_filter(client, catalog):  # noqa: ARG001
    data = fetch(client, execution='2-side')
    assert [c['label'] for c in data['results']] == [
        '334 мм',
        '1284 мм, вертикальный',
    ]
    assert fetch(client, execution='3-side')['count'] == 0
    # 0 — без трубности
    assert [
        c['series'] for c in fetch(client, execution='0-diagonal')['results']
    ] == ['retta']


@pytest.mark.parametrize(
    'params',
    [
        {'height_min': 'abc'},
        {'height_max': 'nan'},
        {'height_min': 'inf'},
        {'power_min': '1e999999'},
        {'tubes': 'x,y'},
        {'page': 'zzz'},
    ],
)
def test_bad_values_ignored(client, catalog, params):  # noqa: ARG001
    assert fetch(client, **params)['count'] == fetch(client)['count'] == 3


def test_page_out_of_range_returns_last(client, catalog):  # noqa: ARG001
    data = fetch(client, page='99')
    assert data['count'] == 3
    assert len(data['results']) == 3


def test_pagination_24_per_page(client, catalog):
    for i in range(30):
        series = Series.objects.create(
            brand=catalog.kzto,
            category=catalog.category,
            slug=f's{i}',
            name=f'S{i}',
            position=10 + i,
        )
        make_variant(series, f'S{i}-1', height_mm=100, price_byn=Decimal(5))
    first = fetch(client)
    assert first['count'] == 33
    assert len(first['results']) == 24
    assert len(fetch(client, page='2')['results']) == 9


def test_brand_returns_model_range(client, catalog):
    SeriesImage.objects.create(
        series=catalog.garmoniya,
        image=png(),
        image_alt='общее',
    )
    # Модельный ряд — все серии бренда, даже если фильтры их скрыли
    data = fetch(client, brand='kzto', height_min='5000')
    assert data['count'] == 0
    assert [t['series'] for t in data['model_range']] == ['garmoniya-a40']
    assert data['model_range'][0]['name'] == 'Гармония А40'
    assert data['model_range'][0]['image']['alt'] == 'общее'
    assert fetch(client)['model_range'] == []


def test_unpublished_and_inactive_hidden(client, catalog):
    data = fetch(client)
    assert 'hidden' not in {c['series'] for c in data['results']}
    assert fetch(client, brand='kzto', height_max='300')['count'] == 0
    Variant.objects.filter(series=catalog.retta).update(is_active=False)
    data = fetch(client)
    assert 'retta' not in {c['series'] for c in data['results']}
    assert [v['value'] for v in facet(data, 'brand')['values']] == ['kzto']
    catalog.kzto.is_published = False
    catalog.kzto.save()
    assert fetch(client)['count'] == 0
    assert fetch(client, brand='kzto')['model_range'] == []


def test_price_on_request_sorted_last(client, catalog):
    nova = Brand.objects.create(slug='nova', name='Nova', note='n')
    series = Series.objects.create(
        brand=nova,
        category=catalog.category,
        slug='nova-x',
        name='Nova X',
        position=0,
    )
    make_variant(series, 'N-1', height_mm=400, price_byn=None)
    data = fetch(client)
    cards = data['results']
    assert cards[-1]['series'] == 'nova-x'
    assert cards[-1]['price_from'] is None
    assert all(c['price_from'] is not None for c in cards[:-1])
    assert facet(data, 'price')['min'] == 100


def test_konvektory_attrs_filters(client, catalog):
    konvektory = Category.objects.create(
        slug='konvektory',
        name='Конвекторы',
        short='к',
        image=png(),
        image_alt='a',
    )
    series = Series.objects.create(
        brand=catalog.kzto,
        category=konvektory,
        slug='floor',
        name='Floor',
    )
    make_variant(
        series,
        'F-1',
        length_mm=1000,
        power_w=900,
        price_byn=Decimal(10),
        attrs={'fan': True, 'voltage': 24, 'grille_type': 'рулонная'},
    )
    make_variant(
        series,
        'F-2',
        length_mm=1500,
        power_w=1300,
        price_byn=Decimal(20),
        attrs={'fan': False, 'voltage': 220, 'grille_type': 'рулонная'},
    )
    data = fetch(client, category='konvektory')
    fan = facet(data, 'fan')['values']
    assert {(v['value'], v['label']) for v in fan} == {
        ('true', 'да'),
        ('false', 'нет'),
    }
    assert [v['value'] for v in facet(data, 'voltage')['values']] == [
        '24',
        '220',
    ]
    assert facet(data, 'length')['max'] == 1500
    assert all(f['key'] != 'height' for f in data['facets'])
    only_fan = fetch(client, category='konvektory', fan='true')
    assert only_fan['count'] == 1
    assert only_fan['results'][0]['price_from'] == 10


def test_unknown_category_uses_radiators_schema(client, catalog):  # noqa: ARG001
    data = client.get(URL, {'category': 'nope'}).json()
    assert data['count'] == 0
    assert 'height' in {f['key'] for f in data['facets']}


def test_query_count_does_not_grow_with_cards(
    client,
    catalog,
    django_assert_max_num_queries,
):
    for i in range(10):
        series = Series.objects.create(
            brand=catalog.kzto,
            category=catalog.category,
            slug=f'q{i}',
            name=f'Q{i}',
        )
        make_variant(series, f'Q{i}-1', height_mm=100, price_byn=Decimal(5))
        Showcase.objects.create(series=series, label='x')
        SeriesImage.objects.create(series=series, image=png(), image_alt='q')
    with django_assert_max_num_queries(18):
        data = fetch(client)
    assert data['count'] == 13


def variants_url(slug='garmoniya-a40'):
    return reverse('series-variants', args=[slug])


def rows_of(client, slug='garmoniya-a40', **params):
    response = client.get(variants_url(slug), params)
    assert response.status_code == 200
    return response.json()


def test_series_detail_shape(client, catalog):
    SeriesImage.objects.create(
        series=catalog.garmoniya,
        image=png(),
        image_alt='чёрный',
        color=catalog.ral9005,
        orientation='h',
    )
    response = client.get(reverse('series-detail', args=['garmoniya-a40']))
    assert response.status_code == 200
    data = response.json()
    assert data['brand'] == {'slug': 'kzto', 'name': 'КЗТО', 'country': ''}
    assert data['category'] == 'radiatory'
    assert data['images'][0]['color'] == 'RAL 9005'
    assert data['images'][0]['orientation'] == 'h'
    assert [g['name'] for g in data['color_groups']] == [
        'Стандартные',
        'Чёрный',
    ]
    assert data['color_groups'][1]['percent'] == 10.0
    assert data['color_groups'][1]['colors'][0]['code'] == 'RAL 9005'
    assert data['ranges']['height'] == [334, 1284]
    assert data['ranges']['area'] == [4, 12.5]
    columns = {c['key'] for c in data['columns']}
    assert {'height', 'power', 'area', 'price'} <= columns
    assert 'color' not in columns
    assert 'brand' not in {f['key'] for f in data['filters']}
    assert 'color' in {f['key'] for f in data['filters']}


def test_series_detail_executions_sorted_by_count(client, catalog):
    make_variant(
        catalog.garmoniya,
        'GA-334-D',
        height_mm=334,
        tubes=2,
        connection='bottom_left',
        price_byn=Decimal(1),
    )
    make_variant(
        catalog.garmoniya,
        'GA-1-P',
        height_mm=100,
        connection='diagonal',
        price_byn=Decimal(1),
    )
    data = client.get(reverse('series-detail', args=['garmoniya-a40'])).json()
    assert [(e['key'], e['count']) for e in data['executions']] == [
        ('2-bottom_left', 3),
        ('2-side', 2),
        ('0-diagonal', 1),
    ]
    assert data['default_execution'] == '2-bottom_left'
    first = data['executions'][0]
    assert first['tubes'] == 2
    assert first['connection'] == 'bottom_left'
    assert first['label'] == '2-трубный, нижнее левое'
    assert data['executions'][2]['label'] == 'диагональное'


@pytest.mark.parametrize('slug', ['hidden', 'nope'])
def test_series_detail_404_unpublished(client, catalog, slug):  # noqa: ARG001
    assert client.get(reverse('series-detail', args=[slug])).status_code == 404
    assert client.get(variants_url(slug)).status_code == 404


def test_variants_row_shape_and_sorting(client, catalog):  # noqa: ARG001
    data = rows_of(client)
    assert data['count'] == 4
    assert [r['article'] for r in data['results']] == [
        'GA-334-S',
        'GA-334-B',
        'GA-1284-S',
        'GA-1284-B',
    ]
    first = data['results'][0]
    assert first['area_m2'] == 4
    assert first['power_w'] == 400
    assert first['tubes'] == 2
    assert first['connection'] == 'side'
    assert first['attrs'] == {}
    assert set(first) >= {
        'article',
        'height_mm',
        'width_mm',
        'depth_mm',
        'length_mm',
        'axis_mm',
        'sections',
        'tubes',
        'thermovalve',
        'orientation',
        'mount',
        'price',
    }
    assert {f['key'] for f in data['facets']} >= {'height', 'color'}
    assert 'brand' not in {f['key'] for f in data['facets']}


def test_variants_default_page_is_20_rows(client, catalog):
    for i in range(21):
        make_variant(
            catalog.retta,
            f'R-{i:02d}',
            height_mm=600 + i,
            price_byn=Decimal(1),
        )
    first = rows_of(client, 'retta')
    assert first['count'] == 23
    assert len(first['results']) == 20
    assert len(rows_of(client, 'retta', page=2)['results']) == 3
    assert len(rows_of(client, 'retta', page='all')['results']) == 23
    assert len(rows_of(client, 'retta', page='zzz')['results']) == 20
    assert len(rows_of(client, 'retta', page=99)['results']) == 3


def test_variants_price_in_color_group(client, catalog):  # noqa: ARG001
    base = rows_of(client)['results'][0]
    assert base['price'] == 101
    black = rows_of(client, color='RAL 9005')['results'][0]
    assert black['price'] == 111
    white = rows_of(client, color='RAL 9016')['results'][0]
    assert white['price'] == 101


def test_variants_price_without_base_group_is_plain(client, catalog):
    catalog.standard.is_base = False
    catalog.standard.save()
    assert rows_of(client)['results'][0]['price'] == 101


def test_variants_any_ral_price_none(client, catalog):
    ral = Color.objects.create(code='RAL 3000', name='Красный', hex='#a00')
    group = ColorGroup.objects.create(
        series=catalog.garmoniya,
        name='По RAL',
        percent=Decimal('30'),
        any_ral=True,
        position=3,
    )
    group.colors.add(ral)
    data = rows_of(client, color='RAL 3000')
    assert data['count'] == 4
    assert {r['price'] for r in data['results']} == {None}
    assert rows_of(client)['results'][0]['price'] == 101


def test_variants_hide_unavailable_color(client, catalog):
    catalog.variants.low_bottom.color_groups.add(catalog.standard)
    data = rows_of(client, color='RAL 9005')
    assert [r['article'] for r in data['results']] == [
        'GA-334-S',
        'GA-1284-S',
        'GA-1284-B',
    ]
    assert rows_of(client, color='RAL 9016')['count'] == 4


def test_variants_execution_and_filters(client, catalog):  # noqa: ARG001
    data = rows_of(client, execution='2-side')
    assert [r['article'] for r in data['results']] == [
        'GA-334-S',
        'GA-1284-S',
    ]
    data = rows_of(client, execution='2-side', height_min=1000)
    assert [r['article'] for r in data['results']] == ['GA-1284-S']


@pytest.mark.parametrize('execution', ['9-nope', 'zzz', '2-'])
def test_unknown_execution_empty_not_400(client, catalog, execution):  # noqa: ARG001
    data = rows_of(client, execution=execution)
    assert data['count'] == 0
    assert data['results'] == []


def test_variants_hide_inactive(client, catalog):
    Variant.objects.filter(pk=catalog.variants.low_side.pk).update(
        is_active=False
    )
    assert rows_of(client)['count'] == 3


def test_variant_detail(client, catalog):
    catalog.variants.low_bottom.color_groups.add(catalog.black)
    url = reverse('variant-detail', args=['GA-334-B'])
    data = client.get(url, {'series': 'garmoniya-a40'}).json()
    assert data['article'] == 'GA-334-B'
    assert data['available_groups'] == [catalog.black.pk]
    assert data['price'] == 132  # базовой нет — единственная доступная
    inherited = client.get(
        reverse('variant-detail', args=['GA-334-S']),
        {'series': 'garmoniya-a40'},
    ).json()
    assert inherited['available_groups'] == [
        catalog.standard.pk,
        catalog.black.pk,
    ]
    assert inherited['price'] == 101


def test_variant_detail_connection_param(client, catalog):
    make_variant(
        catalog.retta,
        'R-TWIN',
        connection='bottom_ends',
        height_mm=500,
        width_mm=580,
    )
    make_variant(
        catalog.retta,
        'R-TWIN',
        connection='side',
        height_mm=580,
        width_mm=500,
    )
    url = reverse('variant-detail', args=['R-TWIN'])
    params = {'series': 'retta'}
    assert client.get(url, params).json()['connection'] == 'side'
    rotated = client.get(url, {**params, 'connection': 'bottom_ends'}).json()
    assert (rotated['height_mm'], rotated['width_mm']) == (500, 580)
    assert (
        client.get(url, {**params, 'connection': 'bottom_left'}).status_code
        == 404
    )


def test_variant_detail_404_for_inactive(client, catalog):
    Variant.objects.filter(pk=catalog.variants.low_side.pk).update(
        is_active=False
    )
    url = reverse('variant-detail', args=['GA-334-S'])
    assert client.get(url, {'series': 'garmoniya-a40'}).status_code == 404


def test_variant_detail_is_scoped_by_series(client, catalog):
    make_variant(catalog.retta, 'GA-334-S', height_mm=1)
    url = reverse('variant-detail', args=['GA-334-S'])
    other = client.get(url, {'series': 'retta'}).json()
    assert other['height_mm'] == 1
    assert client.get(url, {'series': 'nope'}).status_code == 404
    assert client.get(url).status_code == 404
    hidden = reverse('variant-detail', args=['H-1'])
    assert client.get(hidden, {'series': 'hidden'}).status_code == 404


def test_variants_query_count_does_not_grow(
    client,
    catalog,
    django_assert_max_num_queries,
):
    for i in range(30):
        variant = make_variant(
            catalog.garmoniya,
            f'GA-X-{i}',
            height_mm=500 + i,
            price_byn=Decimal(10),
        )
        if i % 2:
            variant.color_groups.add(catalog.black)
    with django_assert_max_num_queries(16):
        data = rows_of(client, page='all', color='RAL 9005')
    assert data['count'] == 34


def test_price_without_color_picks_cheapest_available_group(client, catalog):
    extra = ColorGroup.objects.create(
        series=catalog.garmoniya,
        name='Дорогой',
        percent=Decimal('50'),
        position=3,
    )
    any_ral = ColorGroup.objects.create(
        series=catalog.garmoniya,
        name='RAL',
        percent=Decimal('-5'),
        any_ral=True,
        position=4,
    )
    variant = catalog.variants.low_bottom
    variant.color_groups.add(extra, catalog.black, any_ral)
    url = reverse('variant-detail', args=['GA-334-B'])
    data = client.get(url, {'series': 'garmoniya-a40'}).json()
    assert data['price'] == 132
    rows = rows_of(client)['results']
    assert next(r for r in rows if r['article'] == 'GA-334-B')['price'] == 132


def test_variant_detail_unavailable_color_has_no_price(client, catalog):
    catalog.variants.low_bottom.color_groups.add(catalog.standard)
    url = reverse('variant-detail', args=['GA-334-B'])
    response = client.get(
        url,
        {'series': 'garmoniya-a40', 'color': 'RAL 9005'},
    )
    assert response.status_code == 200
    data = response.json()
    assert data['price'] is None
    assert data['available_groups'] == [catalog.standard.pk]
    ok = client.get(url, {'series': 'garmoniya-a40', 'color': 'RAL 9016'})
    assert ok.json()['price'] == 120


def test_variants_color_is_single_valued(client, catalog):
    catalog.variants.low_bottom.color_groups.add(catalog.standard)
    data = rows_of(client, color='RAL 9005,RAL 9016')
    assert [r['article'] for r in data['results']] == [
        'GA-334-S',
        'GA-1284-S',
        'GA-1284-B',
    ]
    assert data['results'][0]['price'] == 111
    data = rows_of(client, color='RAL 9016,RAL 9005')
    assert data['count'] == 4
    assert data['results'][0]['price'] == 101


def test_null_and_zero_tubes_share_one_execution(client, catalog):
    make_variant(
        catalog.garmoniya,
        'GA-Z-0',
        height_mm=1,
        tubes=0,
        connection='diagonal',
    )
    make_variant(
        catalog.garmoniya,
        'GA-Z-N',
        height_mm=2,
        connection='diagonal',
    )
    data = client.get(reverse('series-detail', args=['garmoniya-a40'])).json()
    keys = [e['key'] for e in data['executions']]
    assert keys.count('0-diagonal') == 1
    assert (
        next(e for e in data['executions'] if e['key'] == '0-diagonal')[
            'count'
        ]
        == 2
    )
