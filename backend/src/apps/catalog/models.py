import re

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from PIL import Image, UnidentifiedImageError

from apps.content.models import (
    MAX_IMAGE_MB,
    Published,
    Sortable,
    Tag,
    WithImage,
)
from apps.core.utils import AutoUploadTo, FileSizeValidator, SizeUnit

LOGO_EXTENSIONS = ['svg', 'png', 'webp']
SVG_TAG = re.compile(rb'<svg\b[^>]*>', re.IGNORECASE)
NUMBER = re.compile(r'[\d.]+')


def svg_attribute(tag: str, name: str) -> str:
    # (?<![\w-]) — чтобы width не нашёлся внутри stroke-width
    match = re.search(rf'(?<![\w-]){name}\s*=\s*["\']([^"\']*)', tag)
    return match[1] if match else ''


def logo_size(file) -> tuple[int, int]:
    """Размеры логотипа для вёрстки: у PNG/WebP — в пикселях,
    у SVG — из viewBox или width/height."""
    file.seek(0)
    if file.name.lower().endswith('.svg'):
        match = SVG_TAG.search(file.read())
        if not match:
            msg = 'Не получилось прочитать SVG'
            raise ValidationError(msg)
        tag = match[0].decode(errors='ignore')
        view_box = svg_attribute(tag, 'viewBox').replace(',', ' ').split()
        if len(view_box) == 4:
            width, height = view_box[2:]
        else:
            width = svg_attribute(tag, 'width')
            height = svg_attribute(tag, 'height')
        sizes = [NUMBER.match(value) for value in (width, height)]
        if not all(sizes):
            msg = 'У SVG нет viewBox или width/height'
            raise ValidationError(msg)
        return tuple(round(float(size[0])) for size in sizes)
    try:
        with Image.open(file) as image:
            return image.size
    except UnidentifiedImageError as error:
        msg = 'Файл не похож на картинку'
        raise ValidationError(msg) from error


class Category(Published, WithImage, Sortable):
    """Разделы каталога. Товары пока в коде фронта и ссылаются на slug."""

    cache_tag = Tag.CATALOG

    name = models.CharField(
        'название',
        max_length=100,
    )
    short = models.CharField(
        'коротко',
        max_length=150,
        help_text='Под названием в плитке на главной',
    )

    class Meta(Sortable.Meta):
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Brand(Published, Sortable):
    """Заводы, за которые ручаемся: главная, «Бренды», фильтры каталога,
    гарантия на «Клиентам»."""

    cache_tag = Tag.CATALOG

    name = models.CharField(
        'название',
        max_length=100,
    )
    country = models.CharField(
        'страна',
        max_length=60,
        blank=True,
    )
    note = models.CharField(
        'подпись',
        max_length=150,
        help_text='Например, «Официальный представитель в Беларуси»',
    )
    logo = models.FileField(
        'логотип',
        upload_to=AutoUploadTo('logo'),
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=LOGO_EXTENSIONS,
                message='Подойдут SVG, PNG или WebP',
            ),
            FileSizeValidator(MAX_IMAGE_MB, SizeUnit.MiB),
        ],
        help_text='Лучше SVG или PNG без фона. Пусто — на сайте название текстом',
    )
    logo_width = models.PositiveIntegerField(
        editable=False,
        null=True,
    )
    logo_height = models.PositiveIntegerField(
        editable=False,
        null=True,
    )
    warranty_years = models.PositiveSmallIntegerField(
        'гарантия до, лет',
        null=True,
        blank=True,
        help_text='Пусто — бренда нет в таблице гарантий',
    )

    class Meta(Sortable.Meta):
        verbose_name = 'бренд'
        verbose_name_plural = 'бренды'

    def __str__(self):
        return self.name

    def clean(self):
        if self.logo and not self.logo._committed:  # noqa: SLF001 — новый файл
            self.logo_width, self.logo_height = logo_size(self.logo)

    def save(self, *args, **kwargs):
        if not self.logo:
            self.logo_width = self.logo_height = None
        elif not self.logo._committed or not self.logo_width:  # noqa: SLF001
            self.logo_width, self.logo_height = logo_size(self.logo)
        super().save(*args, **kwargs)


class LeadTime(Sortable):
    """Ориентир срока изготовления по серии — таблица на «Клиентам»."""

    cache_tag = Tag.CATALOG

    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='lead_times',
        verbose_name='бренд',
    )
    series = models.CharField(
        'серия',
        max_length=150,
        help_text='Как в таблице на сайте, например «Guardo Retta»',
    )
    days = models.PositiveSmallIntegerField(
        'срок, дней',
        null=True,
        blank=True,
        help_text='«До N дней». Пусто — «уточнит менеджер»',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta(Sortable.Meta):
        verbose_name = 'срок изготовления'
        verbose_name_plural = 'сроки изготовления'

    def __str__(self):
        return self.series
