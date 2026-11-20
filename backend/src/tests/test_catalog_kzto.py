import io
from datetime import date
from decimal import Decimal

import pytest
from django.core.management import CommandError, call_command
from PIL import Image

from apps.catalog.importers import kzto
from apps.catalog.importers.kzto_page import parse_page
from apps.catalog.models import (
    Brand,
    Category,
    CurrencyRate,
    Series,
    SeriesFile,
    SeriesImage,
    Subcategory,
    Variant,
)

PICTURE = 'https://kztoradiator.ru/assets/images/resources/1/bat.png'
INTERIOR = 'https://kztoradiator.ru/assets/images/resources/1/room.jpg'
PASSPORT = '/assets/manager/doc/Паспорт BATARÌA.pdf'


def offer(id_, category, name, model, price, **params):
    pictures = ''.join(
        f'<picture>{url}</picture>' for url in params.pop('pictures', [])
    )
    rows = ''.join(
        f'<param name="{key}">{value}</param>' for key, value in params.items()
    )
    model_tag = f'<model>{model}</model>' if model else ''
    return (
        f'<offer id="{id_}" available="true">'
        f'<url>http://kztoradiator.ru/x-{id_}</url><name>{name}</name>'
        f'{model_tag}<price>{price}</price><currencyId>RUR</currencyId>'
        f'<categoryId>{category}</categoryId>{pictures}{rows}</offer>'
    )


def radiator(id_, category, name, model, price, sections, **extra):
    params = {
        kzto.AXIS: '500',
        kzto.FULL_HEIGHT: '576',
        kzto.LENGTH: str(45 * sections),
        kzto.DEPTH: '70',
        kzto.SECTIONS: str(sections),
        kzto.COLUMNS: '2',
        kzto.POWER: str(70 * sections),
        kzto.WEIGHT: '2,37',
        kzto.EXPONENT: '1,24',
        kzto.PRESSURE: '15',
        kzto.WARRANTY: '5',
        **extra,
    }
    return offer(id_, category, name, model, price, **params)


def feed(*offers) -> bytes:
    categories = {
        '1': 'BATARÌA',
        '2': 'Quadrum 30 V',
        '3': 'Quadrum 30 H',
        '4': 'Бриз В',
        '5': 'Решетка Бриз',
        '6': 'Комплектующие',
        '7': 'Новинка',
    }
    tags = ''.join(
        f'<category id="{cid}">{name}</category>'
        for cid, name in categories.items()
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?><yml_catalog><shop>'
        f'<categories>{tags}</categories><offers>{"".join(offers)}</offers>'
        '</shop></yml_catalog>'
    ).encode()


def full_feed() -> bytes:
    return feed(
        radiator(
            1,
            1,
            'Batarìa 2-500-7',
            'БАТ25007',
            '11396',
            7,
            pictures=[PICTURE, INTERIOR],
        ),
        # Ошибка фида: тот же артикул у другого размера
        radiator(2, 1, 'Batarìa 2-500-49', 'БАТ25007', '79772', 49),
        radiator(3, 2, 'Quadrum 30 V 1-300-3', 'К30В13003', '9000', 3),
        radiator(4, 3, 'Quadrum 30 H 1-300-3', 'К30Г13003', '9100', 3),
        offer(
            5,
            4,
            'Бриз В 220V 260х80х800',
            'БРВ26080800',
            '40000',
            **{
                kzto.LENGTH: '800',
                kzto.WIDTH: '260',
                kzto.HEIGHT: '80',
                kzto.FANS: '1',
                kzto.VOLTAGE: '220',
                kzto.POWER: '845',
            },
        ),
        offer(
            6,
            5,
            'Решетка рулонная 200х1000 (5Ал 12)',
            'РБ1921000',
            '5350',
            **{
                kzto.LENGTH: '1000',
                kzto.WIDTH: '192',
                kzto.GRILLE_COVER: 'Алюминий',
                kzto.GRILLE_GAP: '12',
            },
        ),
        offer(7, 6, 'Кронштейн', 'КГ50', '100'),
        offer(8, 7, 'Что-то новое', 'Н1', '100'),
    )


DESCRIPTION = (
    '<div class="catalog-text"><div class="content-style">'
    '<p><strong>Batarìa</strong> — новый этап эволюции.</p>'
    '<ul><li>сталь 2 мм</li><li>три слоя покрытия</li></ul>'
    '</div></div>'
)
PAGE = (
    '<html><body>'
    '<div class="catalog-gall__item"><img src="/a.webp" class="des"/>'
    '<img src="/a-small.webp" class="tab"/></div>'
    # Описание на странице дважды: для компьютера и для телефона
    f'{DESCRIPTION}{DESCRIPTION}'
    '<div class="catalog4-params"><table><tbody>'
    '<tr><td width="217">Материал:</td><td><b>сталь</b></td></tr>'
    '<tr><td>Рабочее давление:</td><td><b>до 15 атм.</b></td></tr>'
    '</tbody></table></div>'
    '<div class="catalog-bottom-text"><div class="content-style">'
    '<p>В комплекте кронштейны и кран Маевского.</p>'
    '<p>- настенные — от 3 секций;</p>'
    '<p><strong>Перед покупкой</strong> ознакомьтесь с паспортом на '
    'закладке Документация.</p>'
    '</div></div>'
    '<a class="job-lvl2-link" href="#">Паспорта</a>'
    f'<a href="{PASSPORT}" class="documentation-pdf__name">'
    ' Паспорт радиатора Bataria </a>'
    '<a href="/assets/manager/doc/obozn.pdf" class="documentation-pdf__name">'
    'Условные обозначения приборов КЗТО</a>'
    '<a href="/assets/manager/doc/table.xlsx" class="documentation-pdf__name">'
    'Паспортная таблица</a>'
    '</body></html>'
)


def image_bytes(size, image_format) -> bytes:
    buffer = io.BytesIO()
    Image.new('RGB', size).save(buffer, image_format)
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / 'media'


@pytest.fixture
def no_revalidate(monkeypatch):
    calls = []
    monkeypatch.setattr(
        kzto.revalidate_frontend,
        'delay',
        lambda tag: calls.append(tag),
    )
    return calls


@pytest.fixture
def site(monkeypatch, no_revalidate):  # noqa: ARG001
    """Сайт завода без сети: адрес → ответ; нет адреса — ошибка сети."""
    pages = {
        kzto.FEED_URL: full_feed(),
        kzto.PAGE_URL.format(1): PAGE.encode(),
        PICTURE: image_bytes((40, 50), 'PNG'),
        'https://kztoradiator.ru/a.webp': image_bytes((40, 50), 'WEBP'),
        INTERIOR: image_bytes((160, 90), 'JPEG'),
        'https://kztoradiator.ru/assets/manager/doc/Паспорт BATARÌA.pdf': (
            b'%PDF-1.4 passport'
        ),
    }
    requested = []

    def fetch(url):
        requested.append(url)
        if url not in pages:
            raise OSError(url)
        return pages[url]

    monkeypatch.setattr(kzto, 'fetch', fetch)
    radiators = Category.objects.create(slug='radiatory', name='Радиаторы')
    Subcategory.objects.create(
        slug='dizajn',
        name='Дизайн-радиаторы',
        category=radiators,
    )
    CurrencyRate.objects.create(
        currency='RUB',
        rate=Decimal('0.036'),
        date=date(2026, 11, 13),
    )
    return pages, requested


def run(*args):
    out = io.StringIO()
    call_command('import_kzto', *args, stdout=out)
    return out.getvalue()


# --- страница серии ---


def test_parse_page():
    page = parse_page(PAGE)

    assert page.description == [
        ('p', 'Batarìa — новый этап эволюции.'),
        ('li', 'сталь 2 мм'),
        ('li', 'три слоя покрытия'),
    ]
    assert page.params == [
        ('Материал', 'сталь'),
        ('Рабочее давление', 'до 15 атм.'),
    ]
    assert page.param('Материал') == 'сталь'
    assert page.gallery == ['/a.webp']
    first = page.documents[0]
    assert (first.section, first.title, first.url) == (
        'Паспорта',
        'Паспорт радиатора Bataria',
        PASSPORT,
    )


def test_page_html_keeps_notes_drops_links_to_their_tabs():
    html = parse_page(PAGE).html()

    assert html == (
        '<p>Batarìa — новый этап эволюции.</p>\n'
        '<ul><li>сталь 2 мм</li><li>три слоя покрытия</li></ul>\n'
        '<h3>Характеристики</h3>\n'
        '<ul><li>Материал: сталь</li><li>Рабочее давление: до 15 атм.</li>'
        '</ul>\n'
        '<p>В комплекте кронштейны и кран Маевского.</p>\n'
        '<ul><li>настенные — от 3 секций;</li></ul>'
    )


# --- фид ---


def test_offer_numbers_accept_comma_and_fallback():
    item = kzto.Offer(
        '1',
        '1',
        'x',
        'x',
        None,
        available=True,
        pictures=[],
        params={kzto.WEIGHT: '2,37', kzto.HEIGHT: '89', kzto.DEPTH: 'н/д'},
    )

    assert item.number(kzto.WEIGHT) == Decimal('2.37')
    assert item.integer(kzto.FULL_HEIGHT, kzto.HEIGHT) == 89
    assert item.integer(kzto.DEPTH) is None


def test_bad_feed():
    with pytest.raises(kzto.FeedError):
        kzto.parse_feed(b'<html>503</html>')
    with pytest.raises(kzto.FeedError):
        kzto.parse_feed(b'not xml')


def test_missing_feed_file(tmp_path):
    with pytest.raises(CommandError):
        run('--feed', str(tmp_path / 'nope.xml'))


# --- импорт ---


@pytest.mark.django_db
@pytest.mark.usefixtures('site')
def test_import_creates_series_and_variants(no_revalidate):
    out = run()

    brand = Brand.objects.get(slug='kzto')
    slugs = set(Series.objects.values_list('slug', flat=True))
    assert slugs == {
        'kzto-bataria',
        'kzto-quadrum-30-v',
        'kzto-quadrum-30-h',
        'kzto-briz-v',
        'kzto-reshetka-briz',
    }
    assert not Series.objects.filter(is_published=True).exists()
    assert Variant.objects.filter(brand=brand).count() == 6

    bataria = Variant.objects.get(article='БАТ25007')
    assert bataria.series.slug == 'kzto-bataria'
    assert (bataria.axis_mm, bataria.height_mm, bataria.width_mm) == (
        500,
        576,
        315,
    )
    assert (bataria.depth_mm, bataria.sections, bataria.tubes) == (70, 7, 2)
    assert bataria.power_w == 490
    assert bataria.price == Decimal('11396')
    assert bataria.currency == 'RUB'
    # Рубли в BYN по курсу Нацбанка, наценка бренда 0 %
    assert bataria.price_byn == Decimal('410.26')
    assert bataria.attrs == {'weight_kg': 2.37, 'exponent_n': 1.24}

    # Повтор артикула в фиде не затирает первый вариант
    twin = Variant.objects.get(article='Batarìa 2-500-49')
    assert twin.sections == 49
    assert 'повтор артикула' in out

    quadrum = Variant.objects.filter(
        series__slug__in=['kzto-quadrum-30-v', 'kzto-quadrum-30-h']
    )
    assert dict(quadrum.values_list('article', 'orientation')) == {
        'К30В13003': 'v',
        'К30Г13003': 'h',
    }
    # Без страницы серии — базовое подключение по положению
    assert dict(quadrum.values_list('article', 'connection')) == {
        'К30В13003': 'side',
        'К30Г13003': 'bottom_ends',
    }
    assert bataria.connection == 'side'

    briz = Variant.objects.get(article='БРВ26080800')
    assert briz.series.category.slug == 'konvektory'
    assert (briz.length_mm, briz.width_mm, briz.height_mm) == (800, 260, 80)
    assert briz.attrs == {'fan': 'с вентилятором', 'voltage': '220 В'}
    assert briz.connection == ''

    grille = Variant.objects.get(article='РБ1921000')
    assert grille.attrs == {
        'grille_type': 'рулонная',
        'grille_material': 'Алюминий',
        'grille_step': '12 мм',
    }

    assert 'Комплектующие (1)' in out
    assert 'Новинка (1)' in out
    assert no_revalidate == ['catalog']


@pytest.mark.django_db
@pytest.mark.usefixtures('site')
def test_import_fills_series_from_page_and_media():
    run()

    series = Series.objects.get(slug='kzto-bataria')
    assert series.subcategory.slug == 'dizajn'
    assert series.material == 'сталь'
    assert series.pressure_bar == 15
    assert series.warranty_years == 5
    assert series.description.startswith(
        '<p>Batarìa — новый этап эволюции.</p>',
    )
    assert 'Характеристики' in series.description

    images = list(SeriesImage.objects.filter(series=series))
    assert [(i.kind, i.image_alt) for i in images] == [
        ('product', 'BATARÌA — фото 1'),
    ]
    assert [(i.image_width, i.image_height) for i in images] == [
        (40, 50),
    ]
    # Только документы серии и только PDF: общие файлы сайта не берём
    files = list(SeriesFile.objects.filter(series=series))
    assert [f.title for f in files] == ['Паспорт радиатора Bataria']


@pytest.mark.django_db
def test_reimport_keeps_manager_edits_and_hides_missing(site):
    pages, _ = site
    run()
    series = Series.objects.get(slug='kzto-bataria')
    series.description = '<p>Свой текст</p>'
    series.is_published = True
    series.save()

    pages[kzto.FEED_URL] = feed(
        radiator(1, 1, 'Batarìa 2-500-7', 'БАТ25007', '12000', 7),
    )
    out = run()

    series.refresh_from_db()
    assert series.description == '<p>Свой текст</p>'
    assert series.is_published
    assert SeriesImage.objects.filter(series=series).count() == 1
    assert SeriesFile.objects.filter(series=series).count() == 1
    assert Variant.objects.get(article='БАТ25007').price == Decimal('12000')
    assert set(
        Variant.objects.filter(is_active=False).values_list(
            'article',
            flat=True,
        ),
    ) == {
        'Batarìa 2-500-49',
        'К30В13003',
        'К30Г13003',
        'БРВ26080800',
        'РБ1921000',
    }
    assert 'скрыто 5' in out


@pytest.mark.django_db
def test_publish_and_dry_run(site, no_revalidate):
    _, requested = site
    run('--dry-run', '--no-pages')
    assert not Series.objects.exists()
    assert not Variant.objects.exists()
    assert no_revalidate == []
    assert requested == [kzto.FEED_URL]

    run('--publish', '--no-media')
    assert Series.objects.filter(is_published=True).count() == 5
    assert not SeriesImage.objects.exists()


@pytest.mark.django_db
def test_page_failure_is_reported(site):
    pages, _ = site
    del pages[kzto.PAGE_URL.format(1)]

    out = run('--no-media')

    assert 'не скачать https://kztoradiator.ru/index.php?id=1' in out
    assert Series.objects.get(slug='kzto-bataria').description == ''


@pytest.mark.parametrize(
    ('url', 'expected'),
    [
        (
            'https://kztoradiator.ruassets/briz/reshetka.png',
            'https://kztoradiator.ru/assets/briz/reshetka.png',
        ),
        (
            'https://kztoradiator.ru/assets/a.png',
            'https://kztoradiator.ru/assets/a.png',
        ),
        ('/assets/doc/a.pdf', 'https://kztoradiator.ru/assets/doc/a.pdf'),
        ('assets/doc/a.pdf', 'https://kztoradiator.ru/assets/doc/a.pdf'),
    ],
)
def test_absolute_url(url, expected):
    assert kzto.absolute(url) == expected


@pytest.mark.parametrize(
    ('text', 'orientation', 'expected'),
    [
        ('боковое (базовое); нижнее (по заказу)', 'v', 'side'),
        ('нижнее, разнесенное по сторонам', 'h', 'bottom_ends'),
        (
            'Нижнее разнесенное по краям (седловое); нижнее правое',
            'h',
            'bottom_ends',
        ),
        ('', 'h', 'bottom_ends'),
        ('', '', 'side'),
    ],
)
def test_connection_from_page(text, orientation, expected):
    target = kzto._radiator('x', 'X', orientation=orientation)  # noqa: SLF001
    page = parse_page(
        '<div class="catalog4-params"><table><tr><td>Подключение '
        f'(Настенное исполнение):</td><td>{text}</td></tr></table></div>',
    )

    assert kzto._connection(target, page) == expected  # noqa: SLF001


@pytest.mark.django_db
@pytest.mark.usefixtures('site')
def test_old_variant_without_connection_is_updated_not_duplicated():
    run('--no-media')
    Variant.objects.filter(article='БАТ25007').update(connection='')

    run('--no-media')

    rows = Variant.objects.filter(article='БАТ25007')
    assert list(rows.values_list('connection', 'is_active')) == [
        ('side', True),
    ]
