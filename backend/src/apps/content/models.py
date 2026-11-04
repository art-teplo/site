from django.contrib.postgres.fields import ArrayField
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from solo.models import SingletonModel

from apps.core.utils import AutoUploadTo, FileSizeValidator, SizeUnit

from .html import clean_html, read_minutes

MAX_IMAGE_MB = 15
IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']
MAX_VIDEO_MB = 100
VIDEO_EXTENSIONS = ['mp4', 'webm']


class Tag:
    """Теги кэша фронта: после правки фронт обновляет страницы с этим тегом
    (cacheTag в web/src/data/api.ts)."""

    SITE = 'site'
    FAQ = 'faq'
    PROJECTS = 'projects'
    POSTS = 'posts'
    SHOWROOM = 'showroom'
    CATALOG = 'catalog'  # бренды, категории, сроки (apps.catalog)


class WithImage(models.Model):
    """Фото в форме ImageAsset фронта: файл, размеры, alt."""

    image = models.ImageField(
        'фото',
        upload_to=AutoUploadTo('image'),
        width_field='image_width',
        height_field='image_height',
        validators=[
            FileExtensionValidator(
                allowed_extensions=IMAGE_EXTENSIONS,
                message='Подойдут JPG, PNG или WebP',
            ),
            FileSizeValidator(MAX_IMAGE_MB, SizeUnit.MiB),
        ],
    )
    image_width = models.PositiveIntegerField(
        editable=False,
        null=True,
    )
    image_height = models.PositiveIntegerField(
        editable=False,
        null=True,
    )
    image_alt = models.CharField(
        'описание фото',
        max_length=200,
        help_text='Что на фото — для незрячих и поисковиков',
    )

    class Meta:
        abstract = True


class Sortable(models.Model):
    position = models.PositiveIntegerField(
        'порядок',
        default=0,
        db_index=True,
    )

    class Meta:
        abstract = True
        ordering = ['position', 'pk']


class SiteSettings(SingletonModel):
    """Контакты и реквизиты — то, что было в web/src/data/site.ts."""

    cache_tag = Tag.SITE

    city = models.CharField(
        'город',
        max_length=100,
        default='Минск',
    )
    address = models.CharField(
        'адрес шоурума',
        max_length=200,
    )
    map_url = models.URLField(
        'ссылка на карту',
        max_length=500,
        blank=True,
    )
    phone = PhoneNumberField(
        'телефон',
        region='BY',
    )
    email = models.EmailField(
        'почта',
    )
    viber_phone = PhoneNumberField(
        'номер Viber',
        region='BY',
        blank=True,
        help_text='Пусто — основной телефон',
    )
    telegram_url = models.URLField(
        'Telegram',
        blank=True,
        help_text='Например, https://t.me/artteplo',
    )
    instagram_url = models.URLField(
        'Instagram',
        blank=True,
    )
    reply_promise = models.CharField(
        'обещание по ответу',
        max_length=200,
        help_text='Под формой заявки',
    )
    legal_name = models.CharField(
        'юрлицо',
        max_length=200,
        blank=True,
    )
    unp = models.CharField(
        'УНП',
        max_length=9,
        blank=True,
        validators=[
            RegexValidator(r'^\d{9}$', 'УНП — 9 цифр'),
        ],
    )
    yandex_org_id = models.CharField(
        'id организации в Яндекс.Картах',
        max_length=32,
        blank=True,
        help_text='Для виджета отзывов',
    )
    showroom_video = models.FileField(
        'видео шоурума',
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
            f'MP4 (H.264), до {MAX_VIDEO_MB} МБ: 1–2 минуты в 1080p. '
            'Пусто — на сайте фото шоурума с подписью «скоро»'
        ),
    )
    showroom_poster = models.ImageField(
        'постер видео',
        upload_to=AutoUploadTo('poster'),
        width_field='showroom_poster_width',
        height_field='showroom_poster_height',
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=IMAGE_EXTENSIONS,
                message='Подойдут JPG, PNG или WebP',
            ),
            FileSizeValidator(MAX_IMAGE_MB, SizeUnit.MiB),
        ],
        help_text='Кадр до запуска, 16:9. Пусто — стандартное фото шоурума',
    )
    showroom_poster_width = models.PositiveIntegerField(
        editable=False,
        null=True,
    )
    showroom_poster_height = models.PositiveIntegerField(
        editable=False,
        null=True,
    )

    class Meta:
        verbose_name = 'настройки сайта'

    def __str__(self):
        return 'Настройки сайта'


class OpeningHours(Sortable):
    cache_tag = Tag.SITE

    settings = models.ForeignKey(
        SiteSettings,
        on_delete=models.CASCADE,
        related_name='hours',
    )
    days = models.CharField(
        'дни',
        max_length=50,
        help_text='Например, Пн–Пт',
    )
    time = models.CharField(
        'время',
        max_length=50,
        help_text='Например, 9:00–18:00 или «выходной»',
    )

    class Meta(Sortable.Meta):
        verbose_name = 'часы работы'
        verbose_name_plural = 'часы работы'

    def __str__(self):
        return f'{self.days}: {self.time}'


class Faq(Sortable):
    cache_tag = Tag.FAQ

    question = models.CharField(
        'вопрос',
        max_length=300,
    )
    answer = models.TextField(
        'ответ',
    )
    on_home = models.BooleanField(
        'на главной',
        default=False,
        help_text='На главной — отмеченные, по порядку; на «Клиентам» — все',
    )

    class Meta(Sortable.Meta):
        verbose_name = 'вопрос'
        verbose_name_plural = 'вопрос-ответ'

    def __str__(self):
        return self.question


class Published(models.Model):
    slug = models.SlugField(
        'адрес',
        max_length=100,
        unique=True,
        help_text='Латиницей, в адресе страницы',
    )
    is_published = models.BooleanField(
        'на сайте',
        default=True,
    )

    class Meta:
        abstract = True


class Project(Published, WithImage, Sortable):
    cache_tag = Tag.PROJECTS

    class Kind(models.TextChoices):
        FLAT = 'flat', 'квартира'
        HOUSE = 'house', 'дом'
        COMPLEX = 'complex', 'ЖК'

    title = models.CharField(
        'название',
        max_length=150,
    )
    kind = models.CharField(
        'тип',
        max_length=16,
        choices=Kind,
    )
    place = models.CharField(
        'место',
        max_length=150,
    )
    # До каталога в базе — slug товаров с фронта
    product_slugs = ArrayField(
        models.CharField(max_length=100),
        verbose_name='товары (slug)',
        default=list,
        blank=True,
    )

    class Meta(Sortable.Meta):
        verbose_name = 'проект'
        verbose_name_plural = 'проекты'

    def __str__(self):
        return self.title


class ProjectPhoto(WithImage, Sortable):
    """Дополнительные фото проекта: на сайте листаются в галерее поверх списка."""

    cache_tag = Tag.PROJECTS

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='photos',
    )

    class Meta(Sortable.Meta):
        verbose_name = 'фото проекта'
        verbose_name_plural = 'ещё фото'

    def __str__(self):
        return self.image_alt


class Post(Published, WithImage):
    cache_tag = Tag.POSTS

    title = models.CharField(
        'заголовок',
        max_length=200,
    )
    published_at = models.DateField(
        'дата',
        default=timezone.localdate,
    )
    lead = models.TextField(
        'лид',
        help_text='Пара предложений под заголовком и в списке статей',
    )
    body = models.TextField(
        'текст',
    )

    class Meta:
        verbose_name = 'статья'
        verbose_name_plural = 'блог'
        ordering = ['-published_at', '-pk']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.body = clean_html(self.body)
        super().save(*args, **kwargs)

    @property
    def read_minutes(self):
        return read_minutes(self.body)


class ShowroomPhoto(WithImage, Sortable):
    cache_tag = Tag.SHOWROOM

    class Meta(Sortable.Meta):
        verbose_name = 'фото шоурума'
        verbose_name_plural = 'шоурум'

    def __str__(self):
        return self.image_alt
