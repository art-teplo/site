"""Разбор строк прайса Guardo и Nova (выгрузка заказчицы в xlsx).

Только чистые функции: строка выгрузки → поля варианта. Запись в базу —
в importers/xlsx.py.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.utils.text import slugify

from ..choices import Connection, Currency, Finish, Heating, Mount, Orientation

COLUMNS = (
    'Название',
    'Активность',
    'Длина, мм',
    'Высота, мм',
    'Ширина, мм',
    'Глубина, мм',
    'Цвет',
    'Межосевое, мм',
    'Мощность, Вт',
    'Тип нагрева',
    'Модель',
    'Бренд',
    'Артикул',
    'Розничная цена',
)
# Бренд в выгрузке → slug и название бренда на сайте
BRANDS = {
    'GUARDO': ('guardo', 'Guardo'),
    'Nova Radiators': ('nova', 'Nova'),
}
RADIATORS = 'radiatory'
TOWEL_RAILS = 'polotentsesushiteli'
TOWEL_RAIL_MODELS = frozenset(
    {'piatto', 'stretto', 'novanta', 'diagonale', 'alto', 'alto q'},
)
# Первая очередь: стекло Santarelli и арматура Multiflex+ не импортируются
SKIP_MODELS = ('santarelli', 'multiflex')

ANY_RAL = '*'
COLOR_CODE_LENGTH = 100  # Color.code
ANY_RAL_COLUMN = 'цвет ral'
CHROME = 'Хром'
GLOSS_SUFFIX = ' глянец'
CONNECTION_RULES = (
    ('под электрику слева', Connection.ELECTRIC_LEFT, False),
    ('под электрику справа', Connection.ELECTRIC_RIGHT, False),
    ('нижнее центральное с вентилем', Connection.BOTTOM_CENTER, True),
    ('нижнее центральное', Connection.BOTTOM_CENTER, False),
    ('нижнее левое', Connection.BOTTOM_LEFT, False),
    ('нижнее правое', Connection.BOTTOM_RIGHT, False),
    ('нижнее по краям', Connection.BOTTOM_ENDS, False),
    ('нижнее в крайних секциях', Connection.BOTTOM_ENDS, False),
    ('нижнее с вентилем', Connection.BOTTOM_UNIVERSAL, True),
    ('нижнее', Connection.BOTTOM_UNIVERSAL, False),
    ('боковое', Connection.SIDE, False),
    ('диагональн', Connection.DIAGONAL, False),
)
CURRENCY_WORDS = (
    ('euro', Currency.EUR),
    ('eur', Currency.EUR),
    ('€', Currency.EUR),
    ('₽', Currency.RUB),
    ('руб', Currency.RUB),
    ('rub', Currency.RUB),
    ('usd', Currency.USD),
    ('$', Currency.USD),
    ('byn', Currency.BYN),
)
TUBE_WORDS = {
    'одно': 1,
    'двух': 2,
    'трех': 3,
    'четырех': 4,
    'пяти': 5,
    'шести': 6,
}

PRICE_NUMBER = re.compile(r'\d[\d\s.,]*')
# Pilon: «2T-0650 15 NKV» — трубность, высота, секции, подключение;
# дальше «3/4"», цвет словами и покраска — цвет берётся из колонки
PILON_ARTICLE = re.compile(r'^(\d)T-\d{4} (\d+) [A-Z]+')
NOVA_TUBES = re.compile(r'^NS-T(\d)')
COLOR_TOKEN = re.compile(
    r'(?<!\S)(?:'
    r'R(?P<ral>\d{4})\((?P<finish>[MGМ])\)'
    r'|(?P<any>RX{3,}|RALX*(?:\s+\((?:H-H|factory paint)\))?)'
    r'|(?P<chrome>CH)'
    r')(?!\S)',
)
TUBES_IN_NAME = re.compile(
    r'(одно|двух|тр[её]х|четыр[её]х|пяти|шести)трубн',
    re.IGNORECASE,
)
SECTIONS_IN_NAME = re.compile(r'(\d+)\s+(?:секци|перекладин)', re.IGNORECASE)
HORIZONTAL = re.compile(r'\bGOR\b')
VERTICAL = re.compile(r'\bVER\b')
FLOOR = re.compile(r'-FL\b')
BK_CODE = re.compile(r'\bBK\b')
DIGITS = re.compile(r'\d+')


@dataclass(slots=True)
class ParsedRow:
    brand_slug: str
    brand_name: str
    series_name: str
    series_slug: str
    category_slug: str
    base_article: str
    color_name: str
    color_code: str
    finish: str
    length_mm: int | None
    height_mm: int | None
    width_mm: int | None
    depth_mm: int | None
    axis_mm: int | None
    power_w: int | None
    tubes: int | None
    sections: int | None
    orientation: str
    mount: str
    connection: str
    thermovalve: bool
    heating: str
    price: Decimal | None
    currency: str
    is_active: bool


def parse_price(text) -> tuple[Decimal, str] | None:
    """«1.613,98 euro», «5 480.00 ₽», «1.001.49 ₽» → (число, валюта).

    Запятая — дробная часть; без запятой все точки, кроме последней, —
    разделители тысяч.
    """
    text = str(text or '').strip()
    match = PRICE_NUMBER.search(text)
    lowered = text.lower()
    currency = next(
        (code for word, code in CURRENCY_WORDS if word in lowered),
        None,
    )
    if match is None or currency is None:
        return None
    number = re.sub(r'\s', '', match.group()).rstrip('.,')
    if ',' in number:
        number = number.replace('.', '').replace(',', '.')
    else:
        whole, dot, fraction = number.rpartition('.')
        number = whole.replace('.', '') + dot + fraction
    try:
        return Decimal(number), currency
    except InvalidOperation:
        return None


def parse_connection(name: str) -> tuple[str, bool]:
    """Подключение и термоклапан — по словам названия: коды в артикуле
    неоднозначны (у Retta «BK-GOR» и боковое, и нижнее по краям)."""
    lowered = (name or '').lower()
    for words, connection, thermovalve in CONNECTION_RULES:
        if words in lowered:
            return str(connection), thermovalve
    return '', False


def clean_text(value) -> str:
    """Значение ячейки строкой без пробелов по краям; пусто — «»."""
    return str(value).strip() if value is not None else ''


def _number(value) -> int | None:
    if isinstance(value, int | float):
        number = round(value)
    else:
        digits = DIGITS.search(clean_text(value))
        number = int(digits.group()) if digits else 0
    return number if number > 0 else None


def _finish(name: str) -> str:
    lowered = name.lower()
    if 'матов' in lowered:
        return Finish.MATTE
    if 'глян' in lowered:
        return Finish.GLOSS
    return ''


def _series(model: str, brand_name: str) -> tuple[str, str]:
    """«GUARDO RETTA 3P» → «Guardo Retta 3P», «PIATTO» → «Guardo Piatto»."""
    words = model.split()
    if words[0].lower() == brand_name.lower():
        words = words[1:]
    words = [
        word.capitalize() if word.isalpha() and len(word) > 1 else word.upper()
        for word in words
    ]
    return ' '.join([brand_name, *words]), ' '.join(words).lower()


def _color(article: str, column: str) -> tuple[str, str, str, str]:
    """Артикул без цвета, код цвета, название и покрытие."""
    pilon = PILON_ARTICLE.match(article)
    if pilon:
        return pilon.group(), column, column, _finish(column)
    token = COLOR_TOKEN.search(article)
    if token:
        base = article[: token.start()] + article[token.end() :]
    elif column and column.lower() in article.lower():
        start = article.lower().index(column.lower())
        base = article[:start] + article[start + len(column) :]
    else:
        base = article
    base = ' '.join(base.split())
    if token and token['ral']:
        gloss = token['finish'] == 'G'
        code = f'RAL {token["ral"]}' + (GLOSS_SUFFIX if gloss else '')
        finish = Finish.GLOSS if gloss else Finish.MATTE
        return base, code, column or code, finish
    if (token and token['any']) or column.lower() == ANY_RAL_COLUMN:
        return base, ANY_RAL, column, ''
    if token and token['chrome']:
        return base, CHROME, column or CHROME, ''
    return base, column, column, _finish(column)


def _heating(value: str) -> str:
    lowered = value.lower()
    if 'электр' in lowered:
        return Heating.ELECTRIC
    if 'водян' in lowered:
        return Heating.WATER
    return ''


def parse_row(row: dict) -> ParsedRow | None:
    """Строка выгрузки → поля варианта; None — строку не импортируем."""
    model = clean_text(row.get('Модель'))
    article = ' '.join(clean_text(row.get('Артикул')).split())
    brand = BRANDS.get(clean_text(row.get('Бренд')))
    if (
        not model
        or not article
        or brand is None
        or model.lower().startswith(SKIP_MODELS)
    ):
        return None
    brand_slug, brand_name = brand
    name = clean_text(row.get('Название'))
    series_name, model_key = _series(model, brand_name)
    base, code, color_name, finish = _color(
        article, clean_text(row.get('Цвет'))
    )

    # Трубность и секции — из названия, у Pilon и Nova есть и в артикуле
    pilon = PILON_ARTICLE.match(article)
    in_article = pilon or NOVA_TUBES.match(article)
    tubes_word = TUBES_IN_NAME.search(name)
    sections_word = SECTIONS_IN_NAME.search(name)
    tubes = sections = None
    if tubes_word:
        tubes = TUBE_WORDS[tubes_word.group(1).lower().replace('ё', 'е')]
    elif in_article:
        tubes = int(in_article.group(1))
    if sections_word:
        sections = int(sections_word.group(1))
    elif pilon:
        sections = int(pilon.group(2))

    if HORIZONTAL.search(article):
        orientation = Orientation.HORIZONTAL
    elif VERTICAL.search(article) or 'вертикальн' in name.lower():
        orientation = Orientation.VERTICAL
    else:
        orientation = ''
    connection, thermovalve = parse_connection(name)
    price = parse_price(row.get('Розничная цена'))
    return ParsedRow(
        brand_slug=brand_slug,
        brand_name=brand_name,
        series_name=series_name,
        series_slug=slugify(series_name),
        category_slug=(
            TOWEL_RAILS if model_key in TOWEL_RAIL_MODELS else RADIATORS
        ),
        base_article=base,
        color_name=color_name,
        color_code=code[:COLOR_CODE_LENGTH],
        finish=finish,
        length_mm=_number(row.get('Длина, мм')),
        height_mm=_number(row.get('Высота, мм')),
        width_mm=_number(row.get('Ширина, мм')),
        depth_mm=_number(row.get('Глубина, мм')),
        axis_mm=_number(row.get('Межосевое, мм')),
        power_w=_number(row.get('Мощность, Вт')),
        tubes=tubes,
        sections=sections,
        orientation=str(orientation),
        mount=Mount.FLOOR if FLOOR.search(article) else '',
        connection=connection,
        thermovalve=thermovalve,
        heating=_heating(clean_text(row.get('Тип нагрева'))),
        price=price[0] if price else None,
        currency=price[1] if price else Currency.BYN,
        is_active=clean_text(row.get('Активность')) == 'Да',
    )
