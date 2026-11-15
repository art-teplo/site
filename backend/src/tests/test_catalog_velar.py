import io
from decimal import Decimal

import pytest
from django.core.management import call_command
from openpyxl import Workbook, load_workbook

from apps.catalog.choices import Connection, Mount
from apps.catalog.importers import velar
from apps.catalog.importers.velar import connection_of
from apps.catalog.models import Color, Series, Variant

PAIRS = ['Наименование', 'Артикул']
TAIL = [
    'Модель',
    'Высота',
    'Кол-во секций',
    'Длина',
    'Цена',
    'Мощность',
    'Глубина',
    'N',
    'E',
    'Итоговая стоимость',
]
ALL_RAL = 'Покраска во ВСЕ ЦВЕТА RAL и VR цвета БЕСПЛАТНО'


def sheet(book, title, codes, rows, note=ALL_RAL, discount=0):
    """Лист как у завода: строка заметок, шапка, строки размеров.
    rows — (артикул без кода, модель, высота, секции, длина, итог, N, E)."""
    ws = book.create_sheet(title)
    ws.append(['БП', 'НИЖНЕЕ', 'Размер скидки =>', discount, note])
    ws.append(PAIRS * len(codes) + TAIL)
    for stem, model, height, sections, length, total, n, e in rows:
        cells = []
        for code in codes:
            article = f'{stem} {code} RAL9016' if code else None
            cells += [f'Радиатор {article}' if article else None, article]
        ws.append(
            [
                *cells,
                model,
                height,
                sections,
                length,
                10000,
                500,
                90,
                n,
                e,
                total,
            ],
        )


@pytest.fixture
def price_file(tmp_path):
    book = Workbook()
    book.remove(book.active)
    sheet(
        book,
        'P30 V',
        ['БП', 'Л50', '050', 'П50', 'ЛП'],
        [('Velar P30 270 V - 2', 'P30 V', 270, 2, 80, 10652, 200, 50)],
    )
    sheet(
        book,
        'P30 H',
        ['БП'],
        [('Velar P30 500 H - 2', 'P30 H', 80, 2, 500, 14305.999, 50, 430)],
        discount=-0.15,
    )
    sheet(
        book,
        'R89 V',
        ['Л109'],
        [('Velar R89 500 V - 2', 'R89 V', 500, 2, 198, '#REF!', None, 109)],
        note='Покраска только в цвета МУАР!!!',
    )
    sheet(
        book,
        'Напольные',
        ['БП', 'ЛП'],
        [
            ('Velar P200 750', 'VELAR P200', 191, None, 750, 31878, 50, 620),
            ('Velar P300 750', 'VELAR P300', 275, None, 750, 55882, 50, 620),
        ],
    )
    sheet(
        book, 'P60-30', ['БП'], [('Velar P60/30-460', 'x', 1, 1, 1, 1, 1, 1)]
    )
    path = tmp_path / 'velar.xlsx'
    book.save(path)
    return path


@pytest.fixture(autouse=True)
def no_revalidate(monkeypatch):
    monkeypatch.setattr(velar.revalidate_frontend, 'delay', lambda tag: tag)


def run(*args) -> str:
    out = io.StringIO()
    call_command('import_velar', *args, stdout=out)
    return out.getvalue()


@pytest.mark.parametrize(
    ('article', 'expected'),
    [
        ('Velar P30 270 V - 2 БП RAL9016', (Connection.SIDE, None)),
        ('Velar P30 270 V - 2 ЛП RAL9016', (Connection.BOTTOM_ENDS, None)),
        ('Velar P30 270 V - 2 Л50 RAL9016', (Connection.BOTTOM_LEFT, 50)),
        ('Velar P30 270 V - 2 П50 RAL9016', (Connection.BOTTOM_RIGHT, 50)),
        ('Velar Q80 500 V - 2 0100 RAL9016', (Connection.BOTTOM_CENTER, 100)),
        ('Velar P200 750 Л50 RAL9016', (Connection.BOTTOM_LEFT, 50)),
        ('Velar P30 270 V - 2 RAL9016', None),
    ],
)
def test_connection_from_article(article, expected):
    assert connection_of(article) == expected


@pytest.mark.django_db
def test_import_series_variants_and_groups(price_file):
    Color.objects.create(code='RAL 9016', name='Белый', hex='#ffffff')
    out = run(str(price_file))

    assert 'пропущены листы: P60-30' in out
    assert 'без цены 1 вариантов' in out
    slugs = set(Series.objects.values_list('slug', flat=True))
    assert slugs == {'velar-p30', 'velar-r89', 'velar-p200', 'velar-p300'}

    p30 = Series.objects.get(slug='velar-p30')
    assert p30.name == 'Velar P30'
    assert not p30.is_published
    assert p30.brand.slug == 'velar'
    assert p30.category.slug == 'radiatory'
    # Вертикальный и горизонтальный листы — одна серия
    assert p30.variants.count() == 6
    # Описание — из прайса: размеры, глубина, подключения
    assert 'Есть вертикальное и горизонтальное исполнение' in p30.description
    assert 'Глубина — 90 мм' in p30.description
    assert 'высота вертикального — 270 мм' in p30.description.lower()
    assert 'любой цвет RAL' in p30.description
    left = p30.variants.get(article='Velar P30 270 V - 2 Л50 RAL9016')
    assert (left.connection, left.axis_mm, left.orientation) == (
        Connection.BOTTOM_LEFT,
        50,
        'v',
    )
    assert (left.height_mm, left.width_mm, left.depth_mm, left.sections) == (
        270,
        80,
        90,
        2,
    )
    # Боковое — межосевое из N, нижнее по краям — из E
    assert (
        p30.variants.get(connection=Connection.SIDE, orientation='v').axis_mm
        == 200
    )
    assert p30.variants.get(connection=Connection.BOTTOM_ENDS).axis_mm == 50
    side_h = p30.variants.get(orientation='h')
    # Цена — «Итоговая стоимость» (со скидкой листа), RUB
    assert (side_h.price, side_h.currency) == (Decimal('14306.00'), 'RUB')
    groups = list(p30.color_groups.values_list('name', 'is_base', 'any_ral'))
    assert groups == [('Стандартные', True, False), ('Любой RAL', False, True)]
    assert list(
        p30.color_groups.get(is_base=True).colors.values_list(
            'code', flat=True
        )
    ) == ['RAL 9016']

    # «Только МУАР» — без «Любого RAL»; «#REF!» — без цены
    r89 = Series.objects.get(slug='velar-r89')
    assert list(r89.color_groups.values_list('name', flat=True)) == [
        'Стандартные'
    ]
    assert r89.variants.get().price is None
    assert '[Уточнить у заказчика' in r89.description

    # Напольные — серия по колонке «Модель»
    p200 = Series.objects.get(slug='velar-p200')
    assert set(p200.variants.values_list('mount', flat=True)) == {Mount.FLOOR}
    assert Series.objects.get(slug='velar-p300').variants.count() == 2


@pytest.mark.django_db
def test_reimport_updates_and_hides_only_own_series(price_file, tmp_path):
    run(str(price_file))
    p30 = Series.objects.get(slug='velar-p30')
    p30.description = 'Правка менеджера'
    p30.save()
    # Трубчатые Velar — из другого файла: повторный импорт их не скрывает
    tubular = Series.objects.create(
        brand=p30.brand,
        category=p30.category,
        name='Velar трубчатый',
        slug='velar-tube',
    )
    other = Variant.objects.create(
        series=tubular,
        brand=p30.brand,
        article='Velar 2057',
    )

    book = load_workbook(price_file)
    book.remove(book['P30 H'])
    book.save(tmp_path / 'next.xlsx')
    out = run(str(tmp_path / 'next.xlsx'))

    assert 'скрыто 1' in out
    p30.refresh_from_db()
    assert p30.description == 'Правка менеджера'
    assert p30.color_groups.count() == 2  # группы не задвоились
    assert not p30.variants.get(orientation='h').is_active
    other.refresh_from_db()
    assert other.is_active


@pytest.mark.django_db
def test_dry_run_saves_nothing(price_file):
    out = run(str(price_file), '--dry-run')
    assert 'Пробный прогон' in out
    assert not Series.objects.exists()
