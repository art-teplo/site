"""Схема категории: какие фильтры и колонки у списка и таблицы вариантов.

Категории меняются редко, поэтому схема в коде, а не в админке.
"""

from dataclasses import dataclass
from typing import Literal

WATTS_PER_M2 = 100
DEFAULT_CATEGORY = 'radiatory'

RANGE = 'range'
LIST = 'list'
COLORS = 'colors'

COLOR_SOURCE = 'color_groups__colors__code'
BRAND_SOURCE = 'series__brand__slug'


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: Literal['range', 'list', 'colors']
    source: str
    unit: str = ''
    column: bool = True
    filter: bool = True
    # Значение поля = значение источника / divisor (площадь = Вт / 100)
    divisor: int = 1


def _range(key, label, source, unit='', **kwargs):
    return Field(key, label, RANGE, source, unit, **kwargs)


def _list(key, label, source, **kwargs):
    return Field(key, label, LIST, source, **kwargs)


PRICE = _range('price', 'Цена', 'price_byn', 'BYN')
HEIGHT = _range('height', 'Высота', 'height_mm', 'мм')
WIDTH = _range('width', 'Ширина', 'width_mm', 'мм')
DEPTH = _range('depth', 'Глубина', 'depth_mm', 'мм')
LENGTH = _range('length', 'Длина', 'length_mm', 'мм')
AXIS = _range('axis', 'Межосевое', 'axis_mm', 'мм')
POWER = _range('power', 'Мощность', 'power_w', 'Вт')
AREA = _range(
    'area',
    'Площадь обогрева',
    'power_w',
    'м²',
    divisor=WATTS_PER_M2,
)
SECTIONS = _range('sections', 'Секции', 'sections')
TUBES = _list('tubes', 'Трубность', 'tubes')
CONNECTION = _list('connection', 'Подключение', 'connection')
ORIENTATION = _list('orientation', 'Положение', 'orientation')
COLOR = Field('color', 'Цвет', COLORS, COLOR_SOURCE)
BRAND = _list('brand', 'Бренд', BRAND_SOURCE)

CATEGORIES: dict[str, list[Field]] = {
    'radiatory': [
        PRICE,
        HEIGHT,
        WIDTH,
        DEPTH,
        AXIS,
        POWER,
        AREA,
        SECTIONS,
        TUBES,
        CONNECTION,
        ORIENTATION,
        COLOR,
        BRAND,
    ],
    'konvektory': [
        LENGTH,
        WIDTH,
        DEPTH,
        POWER,
        _list('fan', 'Вентилятор', 'attrs__fan'),
        _list('voltage', 'Питание', 'attrs__voltage'),
        _list('grille_type', 'Тип решётки', 'attrs__grille_type'),
        _list('grille_material', 'Материал решётки', 'attrs__grille_material'),
        _list('grille_step', 'Шаг решётки', 'attrs__grille_step'),
        COLOR,
        BRAND,
    ],
    'polotentsesushiteli': [
        HEIGHT,
        WIDTH,
        POWER,
        _list('heating', 'Тип нагрева', 'attrs__heating'),
        _list('shape', 'Форма', 'attrs__shape'),
        _list('shelf', 'Полочка', 'attrs__shelf'),
        CONNECTION,
        COLOR,
        BRAND,
    ],
    'armatura': [PRICE, COLOR, BRAND],
}


def for_category(slug: str | None) -> list[Field]:
    return CATEGORIES.get(slug or '', CATEGORIES[DEFAULT_CATEGORY])
