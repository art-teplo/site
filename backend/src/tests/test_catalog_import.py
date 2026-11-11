import io
from datetime import date
from decimal import Decimal

import pytest
from django.core.management import CommandError, call_command
from openpyxl import Workbook

from apps.catalog.importers import parse, xlsx
from apps.catalog.models import (
    Brand,
    Category,
    Color,
    ColorGroup,
    CurrencyRate,
    Series,
    Variant,
)

PILON = 'Трубчатый радиатор GUARDO PILON двухтрубный {h} мм высотой, 204 мм '
PILON += 'шириной, 4 секции, боковое подключение 3/4", {article}'
RETTA = (
    'Трубчатый радиатор с прямоугольным профилем 30х60 GUARDO RETTA 6SP '
    '1500 мм высотой, 300 мм шириной, 4 секции, под электрику слева, '
    '{article}'
)
NOVA = (
    'Трубчатый радиатор Nova Siluet трехтрубный 1500 мм высотой, 515 мм '
    'шириной, 11 секций, нижнее с вентилем подключение, {article}'
)


def row(**fields):
    base = dict.fromkeys(parse.COLUMNS)
    base.update({'Активность': 'Да', 'Тип нагрева': 'Водяной'})
    base.update(fields)
    return base


def pilon(height, suffix, color, price):
    article = f'2T-{height:04d} 4 BK 3/4"{suffix}'
    return row(
        Название=PILON.format(h=height, article=article),
        **{
            'Высота, мм': height,
            'Ширина, мм': 204,
            'Глубина, мм': 65,
            'Межосевое, мм': height - 73,
            'Мощность, Вт': height // 2,
            'Цвет': color,
            'Модель': 'GUARDO PILON',
            'Бренд': 'GUARDO',
            'Артикул': article,
            'Розничная цена': price,
        },
    )


WHITE = ('', 'Белый глянцевый')
BLACK = (' черный матовый K1 (factory paint)', 'Черный матовый')
TECHNOLAK = (' TR (технолак)', 'Бесцветный лак (технолак) глянец')


def retta(code, color, price):
    article = f'6SP-1500-04 E-L {code}'
    return row(
        Название=RETTA.format(article=article),
        **{
            'Высота, мм': 1500,
            'Ширина, мм': 300,
            'Глубина, мм': 57,
            'Мощность, Вт': 524,
            'Тип нагрева': 'Электрический (с ТЭНом)',
            'Цвет': color,
            'Модель': 'GUARDO RETTA 6SP',
            'Бренд': 'GUARDO',
            'Артикул': article,
            'Розничная цена': price,
        },
    )


def guardo_rows():
    return [
        pilon(200, *WHITE, '89,16 euro'),
        pilon(200, *BLACK, '89,16 euro'),
        *[
            pilon(height, *color, price)
            for height in (300, 400, 500)
            for color, price in (
                (WHITE, '100,00 euro'),
                (BLACK, '100,00 euro'),
                (TECHNOLAK, '118,00 euro'),
            )
        ],
        retta('R9016(M)', 'Белый матовый', '33 098.00 ₽'),
        retta('R9005(M)', 'Черный матовый', '33 098.00 ₽'),
        retta('RXXXX', 'Цвет RAL', '36 863.00 ₽'),
        row(Название='Кронштейн', Бренд='GUARDO', Артикул='K-1'),
        row(
            Название='Santarelli',
            Модель='Santarelli Glass',
            Бренд='GUARDO',
            Артикул='S-1',
            **{'Розничная цена': '1 000.00 ₽'},
        ),
        row(
            Название='Клапан',
            Модель='Multiflex+',
            Бренд='GUARDO',
            Артикул='M-1',
            **{'Розничная цена': '1 000.00 ₽'},
        ),
    ]


def write_price(path, sheets):
    book = Workbook()
    book.remove(book.active)
    for title, rows in sheets.items():
        sheet = book.create_sheet(title)
        sheet.append(parse.COLUMNS)
        for item in rows:
            sheet.append([item[column] for column in parse.COLUMNS])
    book.save(path)
    return str(path)


def run(*args):
    out = io.StringIO()
    call_command('import_price', *args, stdout=out)
    return out.getvalue()


@pytest.fixture
def no_revalidate(monkeypatch):
    calls = []
    monkeypatch.setattr(
        xlsx.revalidate_frontend,
        'delay',
        lambda tag: calls.append(tag),
    )
    return calls


@pytest.fixture
def price_file(tmp_path):
    return write_price(tmp_path / 'price.xlsx', {'Guardo': guardo_rows()})


# --- разбор строк ---


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('89,16 euro', (Decimal('89.16'), 'EUR')),
        ('5 480.00 ₽', (Decimal('5480.00'), 'RUB')),
        ('480.00 USD Rostella', (Decimal('480.00'), 'USD')),
        ('1.001.49 ₽', (Decimal('1001.49'), 'RUB')),
        ('1.613,98 euro', (Decimal('1613.98'), 'EUR')),
        ('', None),
        (None, None),
    ],
)
def test_parse_price(text, expected):
    assert parse.parse_price(text) == expected


@pytest.mark.parametrize(
    ('name', 'expected'),
    [
        ('6 секций, под электрику слева', ('electric_left', False)),
        ('6 секций, под электрику справа', ('electric_right', False)),
        ('нижнее центральное с вентилем подключение', ('bottom_center', True)),
        ('Нижнее центральное подключение', ('bottom_center', False)),
        ('нижнее левое подключение', ('bottom_left', False)),
        ('нижнее правое подключение', ('bottom_right', False)),
        ('нижнее по краям подключение', ('bottom_ends', False)),
        ('нижнее в крайних секциях подключение', ('bottom_ends', False)),
        ('нижнее с вентилем подключение', ('bottom_universal', True)),
        ('нижнее с вентилем снизу подключение', ('bottom_universal', True)),
        ('нижнее подключение', ('bottom_universal', False)),
        ('боковое подключение 3/4"', ('side', False)),
        ('диагональное подключение', ('diagonal', False)),
        ('Полотенцесушитель с 5 перекладинами', ('', False)),
    ],
)
def test_parse_connection(name, expected):
    assert parse.parse_connection(name) == expected


def test_parse_row_pilon():
    parsed = parse.parse_row(pilon(200, *WHITE, '89,16 euro'))

    assert parsed.brand_slug == 'guardo'
    assert parsed.series_name == 'Guardo Pilon'
    assert parsed.series_slug == 'guardo-pilon'
    assert parsed.category_slug == 'radiatory'
    assert parsed.base_article == '2T-0200 4 BK'
    assert parsed.color_code == 'Белый глянцевый'
    assert parsed.finish == 'gloss'
    assert parsed.tubes == 2
    assert parsed.sections == 4
    assert parsed.connection == 'side'
    assert parsed.thermovalve is False
    assert parsed.height_mm == 200
    assert parsed.axis_mm == 127
    assert parsed.price == Decimal('89.16')
    assert parsed.currency == 'EUR'
    assert parsed.is_active is True


def test_parse_row_pilon_color_in_article():
    parsed = parse.parse_row(pilon(200, *BLACK, '89,16 euro'))

    assert parsed.base_article == '2T-0200 4 BK'
    assert parsed.color_code == 'Черный матовый'
    assert parsed.finish == 'matte'


def test_parse_row_retta_electric():
    parsed = parse.parse_row(retta('R9016(M)', 'Белый матовый', '33 098.00 ₽'))

    assert parsed.series_slug == 'guardo-retta-6sp'
    assert parsed.series_name == 'Guardo Retta 6SP'
    assert parsed.base_article == '6SP-1500-04 E-L'
    assert parsed.connection == 'electric_left'
    assert parsed.color_code == 'RAL 9016'
    assert parsed.color_name == 'Белый матовый'
    assert parsed.finish == 'matte'
    assert parsed.sections == 4
    assert parsed.tubes is None
    assert (parsed.price, parsed.currency) == (Decimal('33098.00'), 'RUB')


def test_parse_row_gloss_and_any_ral():
    gloss = parse.parse_row(retta('R9016(G)', 'Белый глянцевый', '1 ₽'))
    any_ral = parse.parse_row(retta('RXXXX', 'Цвет RAL', '1 ₽'))

    assert gloss.color_code == 'RAL 9016 глянец'
    assert gloss.finish == 'gloss'
    assert gloss.base_article == any_ral.base_article == '6SP-1500-04 E-L'
    assert any_ral.color_code == parse.ANY_RAL


def test_parse_row_orientation_and_mount():
    parsed = parse.parse_row(
        row(
            Название='Радиатор GUARDO RETTA 3P, нижнее по краям подключение',
            Модель='GUARDO RETTA 3P',
            Бренд='GUARDO',
            Артикул='3P-1400-04 NK-GOR-R-FL R9016(M)',
            Цвет='Белый матовый',
        ),
    )

    assert parsed.base_article == '3P-1400-04 NK-GOR-R-FL'
    assert parsed.orientation == 'h'
    assert parsed.mount == 'floor'
    assert parsed.connection == 'bottom_ends'


def test_parse_row_towel_rail_cyrillic_finish():
    parsed = parse.parse_row(
        row(
            Название=(
                'Полотенцесушитель GUARDO PIATTO 600x330 с 5 перекладинами '
                'белый матовый RAL 9016 (электрический)'
            ),
            Модель='PIATTO',
            Бренд='GUARDO',
            Артикул='PIATTO 0603 E R9016(М)',
            Цвет='Белый матовый',
            **{
                'Тип нагрева': 'Электрический (с ТЭНом)',
                'Розничная цена': '32 082.37 ₽',
            },
        ),
    )

    assert parsed.series_name == 'Guardo Piatto'
    assert parsed.series_slug == 'guardo-piatto'
    assert parsed.category_slug == 'polotentsesushiteli'
    assert parsed.base_article == 'PIATTO 0603 E'
    assert parsed.color_code == 'RAL 9016'
    assert parsed.finish == 'matte'
    assert parsed.sections == 5
    assert parsed.heating == 'electric'


@pytest.mark.parametrize(
    ('article', 'color', 'base', 'code'),
    [
        ('PIATTO 0603 CH', 'Хром', 'PIATTO 0603', 'Хром'),
        (
            'PIATTO 0603 RALXXXX (factory paint)',
            'Цвет RAL',
            'PIATTO 0603',
            parse.ANY_RAL,
        ),
        ('PIATTO 0603 E RALXXX (H-H)', 'Цвет RAL', 'PIATTO 0603 E', 'any'),
        (
            'Diagonale 0805 E RAL (H-H) (тэн)',
            'Цвет RAL',
            'Diagonale 0805 E (тэн)',
            'any',
        ),
        (
            'Alto 2 50х1200 Золото (титан)',
            'Золото',
            'Alto 2 50х1200 (титан)',
            'Золото',
        ),
    ],
)
def test_parse_row_towel_rail_colors(article, color, base, code):
    parsed = parse.parse_row(
        row(Модель='PIATTO', Бренд='GUARDO', Артикул=article, Цвет=color),
    )

    assert parsed.base_article == base
    assert parsed.color_code == (parse.ANY_RAL if code == 'any' else code)


def test_parse_row_nova():
    article = 'NS-T3 1500 11 BV R9010(M)'
    parsed = parse.parse_row(
        row(
            Название=NOVA.format(article=article),
            Модель='Nova Siluet',
            Бренд='Nova Radiators',
            Артикул=article,
            Цвет='Белый молочный матовый RAL9010',
            Активность='Нет',
        ),
    )

    assert parsed.brand_slug == 'nova'
    assert parsed.series_name == 'Nova Siluet'
    assert parsed.series_slug == 'nova-siluet'
    assert parsed.base_article == 'NS-T3 1500 11 BV'
    assert parsed.color_code == 'RAL 9010'
    assert parsed.tubes == 3
    assert parsed.sections == 11
    assert parsed.connection == 'bottom_universal'
    assert parsed.thermovalve is True
    assert parsed.is_active is False


@pytest.mark.parametrize(
    'fields',
    [
        {'Модель': None},
        {'Модель': 'Santarelli Stone'},
        {'Модель': 'Multiflex+'},
    ],
)
def test_parse_row_skips(fields):
    item = pilon(200, *WHITE, '89,16 euro')
    item.update(fields)

    assert parse.parse_row(item) is None


# --- команда ---


@pytest.mark.django_db
@pytest.mark.usefixtures('no_revalidate')
def test_import_creates_series_groups_and_prices(price_file):
    CurrencyRate.objects.create(
        currency='EUR',
        date=date(2026, 11, 11),
        rate=Decimal('3.4'),
    )

    out = run(price_file)

    assert (
        'группа «Бесцветный лак (технолак) глянец +18 %»: +18 %, артикулов 3'
        in out
    )
    assert 'группа «Стандартные»: 0 %, артикулов 4' in out
    assert 'группа «Любой RAL»: по запросу, артикулов 1' in out
    series = {s.slug: s for s in Series.objects.all()}
    assert set(series) == {'guardo-pilon', 'guardo-retta-6sp'}
    pilon_series = series['guardo-pilon']
    assert pilon_series.name == 'Guardo Pilon'
    assert pilon_series.is_published is False
    assert pilon_series.category.slug == 'radiatory'
    assert pilon_series.brand.slug == 'guardo'

    groups = list(pilon_series.color_groups.order_by('position'))
    assert [(g.is_base, g.percent, g.any_ral) for g in groups] == [
        (True, 0, False),
        (False, 18, False),
    ]
    assert groups[0].name == 'Стандартные'
    assert {c.code for c in groups[0].colors.all()} == {
        'Белый глянцевый',
        'Черный матовый',
    }
    assert groups[1].name == 'Бесцветный лак (технолак) глянец +18 %'

    retta_groups = series['guardo-retta-6sp'].color_groups.order_by(
        'position',
    )
    assert [(g.name, g.any_ral) for g in retta_groups] == [
        ('Стандартные', False),
        ('Любой RAL', True),
    ]
    assert not retta_groups[1].colors.exists()

    assert Variant.objects.count() == 5
    variant = Variant.objects.get(article='2T-0300 4 BK')
    assert variant.brand.slug == 'guardo'
    assert variant.price == Decimal('100.00')
    assert variant.currency == 'EUR'
    assert variant.price_byn == Decimal('340.00')
    assert variant.tubes == 2
    assert variant.height_mm == 300
    assert Color.objects.get(code='RAL 9016').finish == 'matte'


def snapshot():
    return {
        'series': Series.objects.count(),
        'variants': Variant.objects.count(),
        'groups': list(
            ColorGroup.objects.order_by('pk').values_list(
                'pk',
                'name',
                'percent',
                'is_base',
                'any_ral',
            ),
        ),
        'group_colors': sorted(
            ColorGroup.colors.through.objects.values_list(
                'colorgroup_id',
                'color_id',
            ),
        ),
        'colors': Color.objects.count(),
        # pk связей: неизменный набор не переписывается удалением и вставкой
        'availability': sorted(
            Variant.color_groups.through.objects.values_list(
                'pk',
                'variant_id',
                'colorgroup_id',
            ),
        ),
        'brands': Brand.objects.count(),
        'categories': Category.objects.count(),
    }


@pytest.mark.django_db
@pytest.mark.usefixtures('no_revalidate')
def test_reimport_is_idempotent_and_keeps_manual_fields(price_file):
    run(price_file)
    series = Series.objects.get(slug='guardo-pilon')
    series.description = '<p>Ручное описание</p>'
    series.is_published = True
    series.save()
    group = series.color_groups.get(is_base=False)
    group.percent = Decimal('25')
    group.name = 'Технолак'
    group.save()
    before = snapshot()

    out = run(price_file)

    series.refresh_from_db()
    group.refresh_from_db()
    assert series.description == '<p>Ручное описание</p>'
    assert series.is_published is True
    assert group.percent == Decimal('25')
    assert group.name == 'Технолак'
    assert snapshot() == before
    assert 'серий новых 0 из 2; вариантов новых 0, обновлено 0, скрыто 0' in (
        out
    )
    assert 'не в группах' not in out


@pytest.mark.django_db
@pytest.mark.usefixtures('no_revalidate')
def test_missing_variant_deactivated(price_file, tmp_path):
    call_command('import_price', price_file)
    other = Brand.objects.create(name='Другой', slug='other')
    Variant.objects.create(
        series=Series.objects.create(
            brand=other,
            category=Series.objects.first().category,
            name='Чужая',
            slug='chuzhaya',
        ),
        article='2T-0200 4 BK',
    )
    rows = [r for r in guardo_rows() if '2T-0200' not in r['Артикул']]
    smaller = write_price(tmp_path / 'smaller.xlsx', {'Guardo': rows})

    call_command('import_price', smaller)

    gone = Variant.objects.get(brand__slug='guardo', article='2T-0200 4 BK')
    assert gone.is_active is False
    assert Variant.objects.get(brand=other).is_active is True
    assert Variant.objects.get(article='2T-0300 4 BK').is_active is True

    call_command('import_price', price_file)

    gone.refresh_from_db()
    assert gone.is_active is True


@pytest.mark.django_db
@pytest.mark.usefixtures('no_revalidate')
def test_partial_color_availability(price_file):
    call_command('import_price', price_file)

    without = Variant.objects.get(article='2T-0200 4 BK')
    full = Variant.objects.get(article='2T-0300 4 BK')
    assert [g.name for g in without.color_groups.all()] == ['Стандартные']
    assert not full.color_groups.exists()


@pytest.mark.django_db
@pytest.mark.usefixtures('no_revalidate')
def test_reimport_lists_new_colors_and_keeps_groups(price_file, tmp_path):
    run(price_file)
    before = snapshot()
    rows = [
        *guardo_rows(),
        pilon(300, ' TR2 (технолак 2)', 'Технолак 2', '117,00 euro'),
        pilon(300, ' GOLD (золото)', 'Золото', '140,00 euro'),
    ]
    bigger = write_price(tmp_path / 'bigger.xlsx', {'Guardo': rows})

    out = run(bigger)

    assert 'guardo-pilon: новые цвета, не в группах: Технолак 2, Золото' in out
    after = snapshot()
    assert after['groups'] == before['groups']
    assert after['group_colors'] == before['group_colors']
    assert after['variants'] == before['variants']
    assert after['availability'] == before['availability']


@pytest.mark.django_db
@pytest.mark.usefixtures('no_revalidate')
def test_manager_group_edits_survive_reimport(price_file):
    run(price_file)
    series = Series.objects.get(slug='guardo-pilon')
    series.color_groups.get(is_base=False).delete()
    base = series.color_groups.get(is_base=True)
    base.colors.remove(Color.objects.get(code='Черный матовый'))

    out = run(price_file)

    assert [g.name for g in series.color_groups.all()] == ['Стандартные']
    assert [c.code for c in base.colors.all()] == ['Белый глянцевый']
    assert (
        'guardo-pilon: новые цвета, не в группах: '
        'Черный матовый, Бесцветный лак (технолак) глянец'
    ) in out
    # Доступность считается только по цветам групп: все варианты полные
    assert not Variant.color_groups.through.objects.exists()


@pytest.mark.django_db
@pytest.mark.usefixtures('no_revalidate')
def test_first_import_skips_negative_and_rare_colors(tmp_path):
    rows = [
        *guardo_rows(),
        # −30 % на трёх артикулах из четырёх — похоже на ошибку прайса
        *[
            pilon(height, ' черный глянец', 'Черный глянцевый', '70,00 euro')
            for height in (300, 400, 500)
        ],
        # +40 %, но только у одного артикула
        pilon(300, ' GOLD (золото)', 'Золото', '140,00 euro'),
    ]
    path = write_price(tmp_path / 'outliers.xlsx', {'Guardo': rows})

    out = run(path)

    series = Series.objects.get(slug='guardo-pilon')
    assert [(g.name, g.percent) for g in series.color_groups.all()] == [
        ('Стандартные', 0),
        ('Бесцветный лак (технолак) глянец +18 %', 18),
    ]
    assert not Color.objects.filter(
        code__in=['Черный глянцевый', 'Золото'],
    ).exists()
    assert (
        'пропущены, проверьте прайс: Черный глянцевый −30 %, артикулов 3'
    ) in out
    assert 'пропущены, проверьте прайс: Золото +40 %, артикулов 1' in out
    # Пропущенные цвета не делают варианты «частичными»
    assert not Variant.objects.get(
        article='2T-0300 4 BK',
    ).color_groups.exists()


@pytest.mark.django_db
def test_import_revalidates_once(
    price_file,
    no_revalidate,
    django_capture_on_commit_callbacks,
):
    with django_capture_on_commit_callbacks(execute=True):
        call_command('import_price', price_file)

    assert no_revalidate == ['catalog']


@pytest.mark.django_db
def test_dry_run_saves_nothing(price_file, no_revalidate):
    before = snapshot()

    out = run(price_file, '--dry-run')

    assert snapshot() == before
    assert before['series'] == before['brands'] == 0
    assert 'Guardo: строк 17; серий новых 2 из 2; вариантов новых 5' in out
    assert 'Пробный прогон' in out
    assert no_revalidate == []


@pytest.mark.django_db
@pytest.mark.usefixtures('no_revalidate')
@pytest.mark.parametrize(
    ('content', 'message'),
    [
        (None, 'Нет файла'),
        (b'not a spreadsheet', 'Не удалось прочитать'),
    ],
)
def test_bad_file_is_a_command_error(tmp_path, content, message):
    path = tmp_path / 'price.xlsx'
    if content is not None:
        path.write_bytes(content)

    with pytest.raises(CommandError, match=message):
        call_command('import_price', str(path))


@pytest.mark.django_db
@pytest.mark.usefixtures('no_revalidate')
def test_sheet_option_limits_import(tmp_path):
    article = 'NS-T3 1500 11 BV R9010(M)'
    nova = row(
        Название=NOVA.format(article=article),
        Модель='Nova Siluet',
        Бренд='Nova Radiators',
        Артикул=article,
        Цвет='Белый молочный матовый RAL9010',
        **{'Розничная цена': '51 747.00 ₽'},
    )
    path = write_price(
        tmp_path / 'both.xlsx',
        {'Guardo': guardo_rows(), 'Nova': [nova]},
    )

    call_command('import_price', path, '--sheet', 'Guardo')
    call_command('import_price', path, '--sheet', 'Nova')

    assert set(Series.objects.values_list('slug', flat=True)) == {
        'guardo-pilon',
        'guardo-retta-6sp',
        'nova-siluet',
    }
    assert Variant.objects.get(brand__slug='nova').article == (
        'NS-T3 1500 11 BV'
    )
    guardo = Variant.objects.filter(brand__slug='guardo')
    assert guardo.count() == guardo.filter(is_active=True).count() == 5


@pytest.mark.django_db
@pytest.mark.usefixtures('no_revalidate')
def test_same_article_rotated_keeps_side_connection(tmp_path):
    def rotated(name, height, width):
        return row(
            Название=f'Радиатор GUARDO RETTA 3P, 3 секции, {name}',
            Модель='GUARDO RETTA 3P',
            Бренд='GUARDO',
            Артикул='3P-0500-03 BK-VER R9016(M)',
            Цвет='Белый матовый',
            **{
                'Высота, мм': height,
                'Ширина, мм': width,
                'Розничная цена': '10 000.00 ₽',
            },
        )

    path = write_price(
        tmp_path / 'rotated.xlsx',
        {
            'Guardo': [
                rotated('нижнее по краям подключение', 130, 500),
                rotated('боковое подключение', 500, 130),
            ],
        },
    )

    call_command('import_price', path)

    variant = Variant.objects.get()
    assert (variant.connection, variant.height_mm) == ('side', 500)


@pytest.mark.django_db
@pytest.mark.usefixtures('no_revalidate')
def test_cheaper_color_does_not_set_base_price(tmp_path):
    def alto(article, color, power, price):
        return row(
            Название='Полотенцесушитель Guardo Alto 1200x82 с 2 перекладинами',
            Модель='Alto',
            Бренд='GUARDO',
            Артикул=article,
            Цвет=color,
            **{
                'Высота, мм': 1200,
                'Мощность, Вт': power,
                'Тип нагрева': 'Электрический (греющий кабель)',
                'Розничная цена': price,
            },
        )

    path = write_price(
        tmp_path / 'alto.xlsx',
        {
            'Guardo': [
                alto('Alto 2 1282 CH', 'Хром', 30, '137.00 USD Rostella'),
                alto(
                    'Alto 2 1282 R9016(M)',
                    'Белый матовый',
                    55,
                    '156.00 USD Rostella',
                ),
            ],
        },
    )

    out = run(path)

    variant = Variant.objects.get()
    assert (variant.price, variant.power_w) == (Decimal('156.00'), 55)
    assert variant.attrs == {'heating': 'electric'}
    assert variant.series.heating == 'electric'
    assert variant.series.category.slug == 'polotentsesushiteli'
    assert [g.name for g in variant.series.color_groups.all()] == [
        'Стандартные',
    ]
    assert 'пропущены, проверьте прайс: Хром −12 %, артикулов 1' in out
