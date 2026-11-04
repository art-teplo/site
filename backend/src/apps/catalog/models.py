from django.core.validators import FileExtensionValidator
from django.db import models

from apps.content.models import (
    MAX_IMAGE_MB,
    Published,
    Sortable,
    Tag,
    WithImage,
)
from apps.core.utils import AutoUploadTo, FileSizeValidator, SizeUnit

LOGO_EXTENSIONS = ['svg', 'png', 'webp']


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
