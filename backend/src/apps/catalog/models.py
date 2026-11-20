from decimal import Decimal

from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.db.models import Q

from apps.content.html import clean_html
from apps.content.models import (
    MAX_IMAGE_MB,
    MAX_VIDEO_MB,
    VIDEO_EXTENSIONS,
    Published,
    Sortable,
    Tag,
    WithImage,
)
from apps.core.utils import AutoUploadTo, FileSizeValidator, SizeUnit

from .choices import Connection, Currency, Finish, Heating, Mount, Orientation

LOGO_EXTENSIONS = ['svg', 'png', 'webp', 'jpg', 'jpeg', 'jfif', 'jpe']
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


class Subcategory(Published, WithImage, Sortable):
    """Тип товара внутри категории: «Трубчатые», «Внутрипольные»."""

    cache_tag = Tag.CATALOG
    IMAGE_HINT = ('Горизонтальное 4:3, от 1000 px по ширине', 1000)

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='types',
        verbose_name='категория',
    )
    name = models.CharField(
        'название',
        max_length=100,
    )
    image = models.ImageField(
        'фото',
        upload_to=AutoUploadTo('image'),
        width_field='image_width',
        height_field='image_height',
        blank=True,
        validators=WithImage._meta.get_field('image').validators,  # noqa: SLF001
        help_text='Необязательно: плитка типа в разделе',
    )
    image_alt = models.CharField(
        'описание фото',
        max_length=200,
        blank=True,
    )

    class Meta(Sortable.Meta):
        verbose_name = 'тип'
        verbose_name_plural = 'типы'

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
                message='Подойдут SVG, PNG, WebP или JPG',
            ),
            FileSizeValidator(MAX_IMAGE_MB, SizeUnit.MiB),
        ],
        help_text='Лучше SVG или PNG без фона; JPG — на белом фоне, на сайте белый растворится в фоне плитки. Пусто — на сайте название текстом',
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


class ProductFamily(models.Model):
    cache_tag = Tag.CATALOG
    brand = models.ForeignKey(
        Brand, on_delete=models.PROTECT, verbose_name='бренд'
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, verbose_name='категория'
    )
    key = models.SlugField('ключ линейки', max_length=100)
    name = models.CharField('линейка', max_length=150)
    presentation_photo = models.ForeignKey(
        'SeriesImage',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name='стилевое фото линейки',
        help_text='Сохраняет выбранное фото плитки независимо от технических галерей исполнений.',
    )

    class Meta:
        verbose_name = 'линейка'
        verbose_name_plural = 'линейки'
        ordering = ['brand', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['brand', 'key'], name='unique_product_family_brand_key'
            )
        ]

    def __str__(self):
        return self.name


class Series(Published, Sortable):
    cache_tag = Tag.CATALOG

    family = models.ForeignKey(
        ProductFamily,
        on_delete=models.PROTECT,
        related_name='series',
        verbose_name='линейка',
        null=True,
        blank=True,
    )
    family_label = models.CharField(
        'подпись в линейке',
        max_length=80,
        blank=True,
        help_text='Название в переключателе моделей, например 350/070. '
        'Если пусто, используется заводское положение или название серии.',
    )
    factory_orientation = models.CharField(
        'заводское положение', max_length=1, choices=Orientation, blank=True
    )
    offer_mode = models.CharField(
        'получение цены',
        max_length=10,
        default='direct',
        choices=[
            ('direct', 'Готовые прайсовые варианты'),
            ('configured', 'База с доплатами'),
        ],
    )

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
    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='series',
        verbose_name='тип',
    )
    name = models.CharField(
        'название',
        max_length=150,
    )
    description = models.TextField(
        'описание',
        blank=True,
    )
    markup_percent = models.DecimalField(
        'наценка, %',
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Для всех вариантов этой серии, после перевода по курсу Нацбанка',
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
    video = models.FileField(
        'видеообзор',
        upload_to=AutoUploadTo('video'),
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=VIDEO_EXTENSIONS,
                message='Подойдут MP4 или WebM',
            ),
            FileSizeValidator(MAX_VIDEO_MB, SizeUnit.MiB),
        ],
        help_text=(
            f'MP4 (H.264), до {MAX_VIDEO_MB} МБ: до 3–4 минут в 1080p. '
            'Постер — первое товарное фото серии. Пусто — раздела нет'
        ),
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

    def clean(self):
        super().clean()
        sub = self.subcategory
        if sub is not None and sub.category_id != self.category_id:
            raise ValidationError(
                {'subcategory': 'Тип относится к другой категории'},
            )
        if self.family_id:
            if self.family.brand_id != self.brand_id:
                raise ValidationError(
                    {'family': 'Линейка относится к другому бренду'}
                )
            if self.family.category_id != self.category_id:
                raise ValidationError(
                    {'family': 'Линейка относится к другой категории'}
                )
        if (
            self.pk
            and self.factory_orientation
            and self.variants.exclude(orientation='')
            .exclude(orientation=self.factory_orientation)
            .exists()
        ):
            raise ValidationError(
                {
                    'factory_orientation': 'Положение противоречит существующим вариантам'
                }
            )
        if (
            self.pk
            and self.offer_mode == 'configured'
            and not self.configured_coverage()
        ):
            raise ValidationError(
                {'offer_mode': 'Базовыми правилами покрыты не все варианты'}
            )

    def configured_coverage(self):
        covered = {
            (tubes, n)
            for tubes, sections in self.connection_options.filter(
                surcharge_rub=0
            ).values_list('tubes', 'allowed_sections')
            for n in sections
        }
        return all(
            pair in covered
            for pair in self.variants.filter(is_active=True)
            .order_by()
            .values_list('tubes', 'sections')
            .distinct()
        )

    def save(self, *args, **kwargs):
        self.description = clean_html(self.description)
        super().save(*args, **kwargs)


class ColorGroup(Sortable):
    cache_tag = Tag.CATALOG

    legacy_origin = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name='edition_copies',
        verbose_name='группа до разделения',
    )

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
                fields=['series', 'legacy_origin'],
                condition=Q(legacy_origin__isnull=False),
                name='unique_edition_color_origin',
            ),
            models.UniqueConstraint(
                fields=['series'],
                condition=Q(is_base=True),
                name='one_base_color_group_per_series',
            ),
        ]

    def __str__(self):
        return f'{self.series}: {self.name}'


class LegacyColorAlias(models.Model):
    parent_slug = models.SlugField(max_length=160)
    old_group_id = models.PositiveBigIntegerField()
    group = models.ForeignKey(
        ColorGroup, on_delete=models.CASCADE, related_name='legacy_aliases'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['parent_slug', 'old_group_id', 'group'],
                name='unique_catalog_legacy_color_alias',
            )
        ]


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
        default=None,
        null=True,
        blank=True,
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

    @property
    def effective_orientation(self):
        return self.orientation or self.series.factory_orientation or None

    def clean(self):
        super().clean()
        if (
            self.orientation
            and self.series_id
            and self.series.factory_orientation
            and self.orientation != self.series.factory_orientation
        ):
            raise ValidationError(
                {
                    'orientation': 'Положение противоречит заводскому исполнению серии'
                }
            )

    def save(self, *args, **kwargs):
        self.brand_id = self.series.brand_id
        super().save(*args, **kwargs)


class ConnectionOption(models.Model):
    """Подтверждённая заводом конфигурация; базовые артикулы не копируются."""

    cache_tag = Tag.CATALOG
    series = models.ForeignKey(
        Series,
        on_delete=models.CASCADE,
        related_name='connection_options',
        verbose_name='серия',
    )
    source_id = models.CharField('код завода', max_length=40)
    label = models.CharField('подключение', max_length=300)
    tubes = models.PositiveSmallIntegerField('рядов в глубину')
    connection = models.CharField(
        'расположение', max_length=20, choices=Connection
    )
    thermovalve = models.BooleanField('встроенный термоклапан', default=False)
    mount = models.CharField('монтаж', max_length=5, choices=Mount)
    surcharge_rub = models.DecimalField(
        'доплата подключения, RUB',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    base_adjustment_rub = models.DecimalField(
        'доплата установки к базе, RUB',
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    allowed_sections = models.JSONField(
        'подтверждённое число секций', default=list
    )
    source_url = models.URLField('источник', max_length=2000)
    checked_on = models.DateField('проверено')
    evidence = models.JSONField(
        'проверка и ограничения', default=dict, blank=True
    )

    class Meta:
        ordering = ['series', 'tubes', 'pk']
        verbose_name = 'подключение серии'
        verbose_name_plural = 'подключения серий'
        constraints = [
            models.UniqueConstraint(
                fields=['series', 'tubes', 'mount', 'source_id'],
                name='unique_factory_connection_option',
            )
        ]

    def __str__(self):
        return f'{self.series}: {self.tubes}, {self.label}'

    def clean(self):
        super().clean()
        sections = self.allowed_sections
        if (
            not isinstance(sections, list)
            or not sections
            or any(type(n) is not int or n <= 0 for n in sections)
            or len(set(sections)) != len(sections)
        ):
            raise ValidationError(
                {
                    'allowed_sections': 'Выберите неповторяющиеся положительные целые числа секций'
                }
            )
        if self.series_id:
            available = set(
                self.series.variants.filter(tubes=self.tubes)
                .order_by()
                .values_list('sections', flat=True)
            )
            if not set(sections) <= available:
                raise ValidationError(
                    {
                        'allowed_sections': 'Таких секций нет у выбранной рядности серии'
                    }
                )
        if self.base_adjustment_rub < 0 or (
            self.surcharge_rub is not None and self.surcharge_rub < 0
        ):
            message = 'Доплата не может быть отрицательной'
            raise ValidationError(message)
        if self.pk and self.series.offer_mode == 'configured':
            previous = (
                type(self)
                .objects.filter(pk=self.pk)
                .values('surcharge_rub')
                .first()
            )
            if previous and previous['surcharge_rub'] == 0:
                covered = {
                    (t, n)
                    for t, ns in self.series.connection_options.exclude(
                        pk=self.pk
                    )
                    .filter(surcharge_rub=0)
                    .values_list('tubes', 'allowed_sections')
                    for n in ns
                }
                if self.surcharge_rub == 0:
                    covered.update((self.tubes, n) for n in sections)
                needed = set(
                    self.series.variants.filter(is_active=True)
                    .order_by()
                    .values_list('tubes', 'sections')
                    .distinct()
                )
                if not needed <= covered:
                    raise ValidationError(
                        {
                            'allowed_sections': 'Базовыми правилами должны быть покрыты все активные типоразмеры'
                        }
                    )


class SeriesImage(WithImage, Sortable):
    cache_tag = Tag.CATALOG
    IMAGE_HINT = (
        'Товарное — 4:3, в интерьере — 16:9, от 1200 px',
        1200,
    )

    class Kind(models.TextChoices):
        PRODUCT = 'product', 'товар'
        INTERIOR = 'interior', 'в интерьере'
        SCHEME = 'scheme', 'схема'

    source_url = models.URLField('источник', max_length=2000, blank=True)
    source_aliases = models.JSONField(default=list, blank=True, editable=False)
    is_visible = models.BooleanField('показывать на сайте', default=True)
    source_sha256 = models.CharField(
        'хеш источника', max_length=64, blank=True
    )

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
    kind = models.CharField(
        'вид фото',
        max_length=10,
        choices=Kind,
        default=Kind.PRODUCT,
        help_text=(
            'Товар — первый экран и карточка; в интерьере — раздел «В '
            'интерьере»; схема подключений — раздел «Подключения», в карточку '
            'и первый экран не попадает'
        ),
    )

    class Meta(Sortable.Meta):
        verbose_name = 'фото серии'
        verbose_name_plural = 'фото серии'
        constraints = [
            models.UniqueConstraint(
                fields=['series', 'source_url'],
                condition=~Q(source_url=''),
                name='unique_series_image_source',
            )
        ]

    def default_alt(self) -> str:
        return self.series.name

    def __str__(self):
        return self.alt


class SeriesFile(Sortable):
    cache_tag = Tag.CATALOG
    is_visible = models.BooleanField('показывать на сайте', default=True)

    source_url = models.URLField('источник', max_length=2000, blank=True)
    source_aliases = models.JSONField(default=list, blank=True, editable=False)
    source_sha256 = models.CharField(
        'хеш источника', max_length=64, blank=True
    )

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
        'документ (PDF или XLSX)',
        upload_to=AutoUploadTo('file'),
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'xlsx'],
                message='Подойдут PDF или XLSX',
            ),
            FileSizeValidator(MAX_PDF_MB, SizeUnit.MiB),
        ],
    )

    class Meta(Sortable.Meta):
        verbose_name = 'файл серии'
        verbose_name_plural = 'файлы серии'
        constraints = [
            models.UniqueConstraint(
                fields=['series', 'source_url'],
                condition=~Q(source_url=''),
                name='unique_series_file_source',
            )
        ]

    def __str__(self):
        return self.title


class Showcase(WithImage, Sortable):
    """Обложка серии для каталога."""

    cache_tag = Tag.CATALOG
    IMAGE_HINT = ('Горизонтальное 4:3, от 1000 px по ширине', 1000)

    series = models.ForeignKey(
        Series,
        on_delete=models.CASCADE,
        related_name='showcases',
        verbose_name='серия',
    )
    label = models.CharField(
        'подпись',
        max_length=150,
        blank=True,
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
        help_text='Пусто — сайт подберёт товарное фото из галереи серии',
    )
    image_alt = models.CharField(
        'описание фото',
        max_length=200,
        blank=True,
    )

    def default_alt(self) -> str:
        return self.series.name

    class Meta(Sortable.Meta):
        verbose_name = 'витрина'
        verbose_name_plural = 'витрины'

    def __str__(self):
        return self.series.name


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
