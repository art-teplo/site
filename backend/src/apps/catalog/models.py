from decimal import Decimal

from django.contrib.postgres.indexes import GinIndex
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.db.models import Q

from apps.content.html import clean_html
from apps.content.models import (
    MAX_IMAGE_MB,
    Published,
    Sortable,
    Tag,
    WithImage,
)
from apps.core.utils import AutoUploadTo, FileSizeValidator, SizeUnit

from .choices import Connection, Currency, Finish, Heating, Mount, Orientation

LOGO_EXTENSIONS = ['svg', 'png', 'webp']
MAX_PDF_MB = 20


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
    markup_percent = models.DecimalField(
        'наценка, %',
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Добавляется к цене после перевода по курсу Нацбанка',
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


class Color(models.Model):
    cache_tag = Tag.CATALOG

    code = models.CharField(
        'код',
        max_length=100,
        unique=True,
        help_text='«RAL 9016» или название, например «Кофейный муар»',
    )
    name = models.CharField(
        'название',
        max_length=100,
    )
    hex = models.CharField(
        'цвет на экране',
        max_length=7,
        validators=[
            RegexValidator(
                r'^#[0-9a-fA-F]{6}$',
                message='Формат #rrggbb',
            ),
        ],
    )
    finish = models.CharField(
        'покрытие',
        max_length=10,
        choices=Finish,
        blank=True,
    )

    class Meta:
        ordering = ['code']
        verbose_name = 'цвет'
        verbose_name_plural = 'цвета'

    def __str__(self):
        return self.code


class Series(Published, Sortable):
    cache_tag = Tag.CATALOG

    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name='series',
        verbose_name='бренд',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='series',
        verbose_name='категория',
    )
    name = models.CharField(
        'название',
        max_length=150,
    )
    description = models.TextField(
        'описание',
        blank=True,
    )
    material = models.CharField(
        'материал',
        max_length=100,
        blank=True,
    )
    heating = models.CharField(
        'тип обогрева',
        max_length=10,
        choices=Heating,
        default=Heating.WATER,
    )
    pressure_bar = models.PositiveSmallIntegerField(
        'рабочее давление, бар',
        null=True,
        blank=True,
    )
    warranty_years = models.PositiveSmallIntegerField(
        'гарантия, лет',
        null=True,
        blank=True,
        help_text='Пусто — как у бренда',
    )
    video_url = models.URLField(
        'видео',
        blank=True,
    )

    class Meta(Sortable.Meta):
        verbose_name = 'серия'
        verbose_name_plural = 'серии'

    def __str__(self):
        return self.name

    @property
    def warranty(self) -> int | None:
        if self.warranty_years is not None:
            return self.warranty_years
        return self.brand.warranty_years

    def save(self, *args, **kwargs):
        self.description = clean_html(self.description)
        super().save(*args, **kwargs)


class ColorGroup(Sortable):
    cache_tag = Tag.CATALOG

    series = models.ForeignKey(
        Series,
        on_delete=models.CASCADE,
        related_name='color_groups',
        verbose_name='серия',
    )
    name = models.CharField(
        'название',
        max_length=100,
    )
    percent = models.DecimalField(
        'наценка за цвет, %',
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    colors = models.ManyToManyField(
        Color,
        blank=True,
        related_name='color_groups',
        verbose_name='цвета',
    )
    is_base = models.BooleanField(
        'базовая',
        default=False,
        help_text='Цена серии «от» считается в базовой группе',
    )
    any_ral = models.BooleanField(
        'любой RAL',
        default=False,
        help_text='Цена по запросу',
    )

    class Meta(Sortable.Meta):
        verbose_name = 'группа цветов'
        verbose_name_plural = 'группы цветов'
        constraints = [
            models.UniqueConstraint(
                fields=['series'],
                condition=Q(is_base=True),
                name='one_base_color_group_per_series',
            ),
        ]

    def __str__(self):
        return f'{self.series}: {self.name}'


class Variant(models.Model):
    """Типоразмер серии. Правятся массово (импорт) — сброс кэша не по
    сигналу, а один раз после пачки."""

    series = models.ForeignKey(
        Series,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='серия',
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name='variants',
        editable=False,
        verbose_name='бренд',
        help_text='Копия бренда серии — для уникальности артикула',
    )
    article = models.CharField(
        'артикул',
        max_length=100,
    )
    is_active = models.BooleanField(
        'в продаже',
        default=True,
    )
    height_mm = models.PositiveIntegerField(
        'высота, мм', null=True, blank=True
    )
    width_mm = models.PositiveIntegerField('ширина, мм', null=True, blank=True)
    depth_mm = models.PositiveIntegerField(
        'глубина, мм', null=True, blank=True
    )
    length_mm = models.PositiveIntegerField('длина, мм', null=True, blank=True)
    axis_mm = models.PositiveIntegerField(
        'межосевое, мм',
        null=True,
        blank=True,
    )
    sections = models.PositiveIntegerField('секций', null=True, blank=True)
    power_w = models.PositiveIntegerField(
        'мощность, Вт', null=True, blank=True
    )
    tubes = models.PositiveIntegerField('трубок', null=True, blank=True)
    connection = models.CharField(
        'подключение',
        max_length=20,
        choices=Connection,
        blank=True,
    )
    thermovalve = models.BooleanField(
        'с термоклапаном',
        default=False,
    )
    orientation = models.CharField(
        'ориентация',
        max_length=1,
        choices=Orientation,
        blank=True,
    )
    mount = models.CharField(
        'монтаж',
        max_length=5,
        choices=Mount,
        blank=True,
    )
    price = models.DecimalField(
        'цена в прайсе',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(
        'валюта прайса',
        max_length=3,
        choices=Currency,
        default=Currency.BYN,
    )
    price_byn = models.DecimalField(
        'цена, BYN',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        editable=False,
    )
    attrs = models.JSONField(
        'прочие характеристики',
        default=dict,
        blank=True,
    )
    color_groups = models.ManyToManyField(
        ColorGroup,
        blank=True,
        related_name='variants',
        verbose_name='группы цветов',
        help_text='Пусто — доступны все группы серии',
    )

    class Meta:
        ordering = ['series', 'height_mm', 'power_w', 'pk']
        verbose_name = 'вариант'
        verbose_name_plural = 'варианты'
        constraints = [
            models.UniqueConstraint(
                fields=['brand', 'article', 'connection'],
                name='unique_article_connection_per_brand',
            ),
        ]
        indexes = [
            models.Index(fields=['series', 'is_active']),
            models.Index(fields=['height_mm']),
            models.Index(fields=['power_w']),
            models.Index(fields=['price_byn']),
            GinIndex(fields=['attrs'], name='variant_attrs_gin'),
        ]

    def __str__(self):
        if self.connection:
            return f'{self.article} · {self.get_connection_display()}'
        return self.article

    def save(self, *args, **kwargs):
        self.brand_id = self.series.brand_id
        super().save(*args, **kwargs)


class SeriesImage(WithImage, Sortable):
    cache_tag = Tag.CATALOG

    series = models.ForeignKey(
        Series,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='серия',
    )
    color = models.ForeignKey(
        Color,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='цвет',
    )
    orientation = models.CharField(
        'ориентация',
        max_length=1,
        choices=Orientation,
        blank=True,
    )

    class Meta(Sortable.Meta):
        verbose_name = 'фото серии'
        verbose_name_plural = 'фото серии'

    def __str__(self):
        return self.image_alt


class SeriesFile(Sortable):
    cache_tag = Tag.CATALOG

    series = models.ForeignKey(
        Series,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name='серия',
    )
    title = models.CharField(
        'название',
        max_length=150,
    )
    file = models.FileField(
        'PDF',
        upload_to=AutoUploadTo('file'),
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf'],
                message='Подойдёт только PDF',
            ),
            FileSizeValidator(MAX_PDF_MB, SizeUnit.MiB),
        ],
    )

    class Meta(Sortable.Meta):
        verbose_name = 'файл серии'
        verbose_name_plural = 'файлы серии'

    def __str__(self):
        return self.title


class Showcase(WithImage, Sortable):
    """Витрина серии: подпись и вариант, который она показывает."""

    cache_tag = Tag.CATALOG

    series = models.ForeignKey(
        Series,
        on_delete=models.CASCADE,
        related_name='showcases',
        verbose_name='серия',
    )
    label = models.CharField(
        'подпись',
        max_length=150,
    )
    variant = models.ForeignKey(
        Variant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='вариант',
    )
    image = models.ImageField(
        'фото',
        upload_to=AutoUploadTo('image'),
        width_field='image_width',
        height_field='image_height',
        blank=True,
        validators=WithImage._meta.get_field('image').validators,  # noqa: SLF001
        help_text='Пусто — первое фото серии',
    )
    image_alt = models.CharField(
        'описание фото',
        max_length=200,
        blank=True,
    )

    class Meta(Sortable.Meta):
        verbose_name = 'витрина'
        verbose_name_plural = 'витрины'

    def __str__(self):
        return self.label


class CurrencyRate(models.Model):
    currency = models.CharField(
        'валюта',
        max_length=3,
        choices=[c for c in Currency.choices if c[0] != Currency.BYN],
    )
    rate = models.DecimalField(
        'курс, BYN за единицу',
        max_digits=14,
        decimal_places=6,
    )
    date = models.DateField('дата')

    class Meta:
        ordering = ['-date', 'currency']
        verbose_name = 'курс Нацбанка'
        verbose_name_plural = 'курсы Нацбанка'
        constraints = [
            models.UniqueConstraint(
                fields=['currency', 'date'],
                name='unique_rate_per_day',
            ),
        ]

    def __str__(self):
        return f'{self.currency} {self.rate} на {self.date}'

    @classmethod
    def latest(cls, currency: str) -> Decimal | None:
        return (
            cls.objects.filter(currency=currency)
            .order_by('-date')
            .values_list('rate', flat=True)
            .first()
        )
