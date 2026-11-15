import io

from PIL import Image, ImageDraw

from apps.catalog.photos import trim_white


def encode(image: Image.Image, image_format: str = 'JPEG') -> bytes:
    out = io.BytesIO()
    image.save(out, image_format)
    return out.getvalue()


def padded(size, box, image_format='JPEG', mode='RGB'):
    """Белый холст size с тёмным кадром в box."""
    white = (255, 255, 255, 255) if mode == 'RGBA' else (255, 255, 255)
    image = Image.new(mode, size, white)
    ImageDraw.Draw(image).rectangle(box, fill=(60, 70, 80))
    return encode(image, image_format)


def test_side_bands_are_cut():
    # Вертикальный кадр 100×120, дополненный белым до 300×120
    result = trim_white(padded((300, 120), (100, 0, 199, 119)))
    assert result is not None
    assert (result.width, result.height) == (100, 120)
    with Image.open(io.BytesIO(result.data)) as image:
        assert image.format == 'JPEG'
        assert image.size == (100, 120)


def test_top_and_bottom_bands_are_cut():
    result = trim_white(padded((200, 300), (0, 50, 199, 249), 'PNG'))
    assert result is not None
    assert (result.width, result.height) == (200, 200)


def test_product_on_white_is_kept():
    # Белое со всех сторон — товар на белом фоне, воздух вокруг не режем
    assert trim_white(padded((300, 300), (100, 100, 199, 199))) is None


def test_thin_light_edge_is_kept():
    # Полоса в 1 % ширины — светлый край кадра, а не поле
    assert trim_white(padded((300, 120), (3, 0, 296, 119))) is None


def test_full_frame_and_transparent_png_are_kept():
    assert trim_white(padded((300, 120), (0, 0, 299, 119))) is None
    transparent = padded((300, 120), (100, 0, 199, 119), 'PNG', mode='RGBA')
    assert trim_white(transparent) is None
