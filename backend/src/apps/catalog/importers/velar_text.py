"""Описание серии Velar: профиль — по сайту завода velarwh.ru, размеры,
глубина, секции и подключения — из строк прайса. Пишется, только если
описание серии пустое: дальше текст правит менеджер в админке."""

from ..choices import Connection, Mount, Orientation

PROFILE = {
    'velar-p30': 'с прямоугольным профилем',
    'velar-p60': 'с широким прямоугольным профилем',
    'velar-s': 'с профилем со скруглёнными углами',
    'velar-sp': 'с овальным профилем',
    'velar-q40': 'с квадратным профилем',
    'velar-q60': 'с квадратным профилем',
    'velar-q80': 'с крупным квадратным профилем',
    'velar-r32': 'с круглой трубой',
    'velar-r42': 'с круглой трубой',
    'velar-r89': 'с круглой трубой крупного диаметра',
    'velar-rt1': 'с круглой трубой',
    'velar-rt2': 'с круглой трубой в два ряда',
    'velar-rt1w': 'с круглой трубой',
    'velar-rt2w': 'с круглой трубой в два ряда',
    'velar-qt1': 'с квадратным профилем',
    'velar-qt2': 'с квадратным профилем в два ряда',
    'velar-p200': 'с прямоугольным профилем',
    'velar-p300': 'с прямоугольным профилем',
    'velar-q500': 'с квадратным профилем',
}
# Чем W-исполнение отличается от обычного, на сайте завода не сказано
NOTES = {
    'velar-rt1w': '[Уточнить у заказчика: чем RT1W отличается от RT1]',
    'velar-rt2w': '[Уточнить у заказчика: чем RT2W отличается от RT2]',
}
CONNECTIONS = (
    (Connection.SIDE, 'боковое'),
    (Connection.BOTTOM_LEFT, 'нижнее слева'),
    (Connection.BOTTOM_RIGHT, 'нижнее справа'),
    (Connection.BOTTOM_CENTER, 'нижнее по центру'),
    (Connection.BOTTOM_ENDS, 'нижнее по краям'),
)
ANY_RAL = 'Красится на заводе порошковой краской в любой цвет RAL без доплаты.'
ONLY_PAINT = (
    'Красится на заводе порошковой краской. '
    '[Уточнить у заказчика: в какие цвета «муар» красится модель]'
)


def _span(values, unit='мм') -> str:
    values = sorted({v for v in values if v})
    if not values:
        return ''
    if values[0] == values[-1]:
        return f'{values[0]} {unit}'
    return f'от {values[0]} до {values[-1]} {unit}'


def describe(slug: str, name: str, rows, *, any_ral: bool) -> str:
    """rows — строки прайса серии (Row из velar.py)."""
    values = [row.values for row in rows]
    by_orientation = {
        o: [v for v in values if v['orientation'] == o]
        for o in (Orientation.VERTICAL, Orientation.HORIZONTAL)
    }
    floor = any(v['mount'] == Mount.FLOOR for v in values)
    found = {v['connection'] for v in values}
    connections = [label for code, label in CONNECTIONS if code in found]
    second = _sizes(values, by_orientation, floor=floor)
    if connections:
        second.append(f'Подключение: {", ".join(connections)}.')
    second.append('По заказу комплектуется электрическим ТЭНом.')
    paint = ANY_RAL if any_ral else ONLY_PAINT
    parts = (_intro(slug, name, values, by_orientation, floor=floor), second)
    return ''.join(f'<p>{" ".join(part)}</p>' for part in (*parts, [paint]))


def _intro(slug, name, values, by_orientation, *, floor) -> list[str]:
    lead = f'{name} — стальной трубчатый радиатор {PROFILE.get(slug, "")}'
    if floor:
        kind = 'Напольный.'
    elif all(by_orientation.values()):
        kind = 'Есть вертикальное и горизонтальное исполнение.'
    elif by_orientation[Orientation.VERTICAL]:
        kind = 'Вертикальный.'
    else:
        kind = 'Горизонтальный.'
    result = [f'{lead.rstrip()}. {kind}']
    depth = _span(v['depth_mm'] for v in values)
    if depth:
        result.append(f'Глубина — {depth}.')
    if slug in NOTES:
        result.append(NOTES[slug])
    return result


def _sizes(values, by_orientation, *, floor) -> list[str]:
    sizes = []
    vertical = by_orientation[Orientation.VERTICAL]
    horizontal = by_orientation[Orientation.HORIZONTAL]
    both = bool(vertical and horizontal)
    if vertical and not floor:
        label = 'высота вертикального' if both else 'высота'
        sizes.append(f'{label} — {_span(v["height_mm"] for v in vertical)}')
    if horizontal:
        label = 'длина горизонтального' if both else 'длина'
        sizes.append(f'{label} — {_span(v["width_mm"] for v in horizontal)}')
    sections = _span((v['sections'] for v in values), unit='').strip()
    if sections:
        sizes.append(f'секций — {sections}')
    if not sizes:
        return []
    text = '; '.join(sizes)
    return [f'{text[0].upper()}{text[1:]}.']
