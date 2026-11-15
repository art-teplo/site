"""Белые поля, «вшитые» в фото.

На сайте завода часть фото — вертикальный кадр, дополненный белым до
горизонтального (Quadrum 60, РСК): в карточке это белые полосы по бокам.
Срезаем такие поля, а фото, которое не влезает в рамку, сайт покажет на
размытом фоне.
"""

import io
from dataclasses import dataclass

from PIL import Image, ImageChops

WHITE_TOLERANCE = 12  # отличие от белого, ниже которого пиксель — поле
MIN_BAND = 0.03  # поле уже 3 % стороны — не поле, а светлый край кадра
SAVE_OPTIONS = {
    'JPEG': {'quality': 90, 'optimize': True},
    'PNG': {'optimize': True},
    'WEBP': {'quality': 90},
}


@dataclass(frozen=True)
class Trimmed:
    data: bytes
    width: int
    height: int


def _has_alpha(image: Image.Image) -> bool:
    return image.mode in {'RGBA', 'LA'} or (
        image.mode == 'P' and 'transparency' in image.info
    )


def white_box(image: Image.Image) -> tuple[int, int, int, int] | None:
    """Рамка кадра без белых полей; None — полей нет или фото прозрачное."""
    if _has_alpha(image):
        return None  # у PNG без фона «поле» — прозрачность, не белое
    rgb = image.convert('RGB')
    white = Image.new('RGB', rgb.size, (255, 255, 255))
    mask = (
        ImageChops.difference(rgb, white)
        .convert('L')
        .point(lambda v: 255 if v > WHITE_TOLERANCE else 0)
    )
    box = mask.getbbox()
    if box is None:
        return None  # кадр целиком белый
    width, height = rgb.size
    left, top, right, bottom = box
    # Узкая светлая кромка — часть кадра, режем только настоящие поля
    left = left if left >= width * MIN_BAND else 0
    top = top if top >= height * MIN_BAND else 0
    right = right if width - right >= width * MIN_BAND else width
    bottom = bottom if height - bottom >= height * MIN_BAND else height
    sides = (left, top, right, bottom) != (0, top, width, bottom)
    ends = (left, top, right, bottom) != (left, 0, right, height)
    # Поля — только по бокам или только сверху и снизу. Белое со всех сторон —
    # товар на белом фоне: его не трогаем, иначе срежем воздух вокруг товара
    if sides == ends:
        return None
    return left, top, right, bottom


def trim_white(data: bytes) -> Trimmed | None:
    """Фото без белых полей в том же формате; None — резать нечего."""
    with Image.open(io.BytesIO(data)) as image:
        image_format = image.format
        box = white_box(image)
        if box is None or image_format not in SAVE_OPTIONS:
            return None
        cropped = image.crop(box)
        out = io.BytesIO()
        if image_format == 'JPEG' and cropped.mode not in {'RGB', 'L'}:
            cropped = cropped.convert('RGB')
        cropped.save(out, image_format, **SAVE_OPTIONS[image_format])
        return Trimmed(out.getvalue(), *cropped.size)
