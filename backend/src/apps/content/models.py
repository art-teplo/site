from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from solo.models import SingletonModel

from apps.core.utils import AutoUploadTo, FileSizeValidator, SizeUnit

from .html import clean_html, read_minutes

MAX_IMAGE_MB = 15
IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'jfif', 'jpe', 'png', 'webp']
MAX_VIDEO_MB = 250
VIDEO_EXTENSIONS = ['mp4', 'webm']
FOCUS_CENTER = '50 50'
FOCUS_PATTERN = r'^(100|[1-9]?\d) (100|[1-9]?\d)$'


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
    # Необязательное: пусто — сайт подписывает фото default_alt() (название записи).
    # Описание помогает поиску по картинкам и незрячим, но без него фото не пропадает
    image_alt = models.CharField(
        'описание фото',
        max_length=200,
        blank=True,
        help_text='Что на фото — для поиска по картинкам и незрячих. '
        'Пусто — подпишется названием',
    )
    # Рамки на сайте фиксированной формы (4:5, 4:3, 16:9), фото заполняет
    # рамку и обрезается: фокус — что остаётся в кадре (object-position)
    image_focus = models.CharField(
        'точка фокуса',
        max_length=7,
        default=FOCUS_CENTER,
        validators=[
            RegexValidator(
                FOCUS_PATTERN,
                message='Два числа от 0 до 100 через пробел: «50 50»',
            ),
        ],
        help_text=(
            'Нажмите на фото там, где главное (обычно радиатор): '
            'при обрезке под рамку оно останется в кадре'
        ),
    )

    # Подсказка к полю «фото» в админке и ширина, меньше которой фото
    # на сайте будет мыльным: (текст, px). У каждой модели — своя рамка
    IMAGE_HINT: tuple[str, int] = ('', 0)

    class Meta:
        abstract = True

    def default_alt(self) -> str:
        """Подпись фото, если «описание фото» не заполнили: название записи."""
        return getattr(self, 'title', '') or getattr(self, 'name', '') or ''

    @property
    def alt(self) -> str:
        return self.image_alt or self.default_alt()


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
    yandex_org_id = models.PositiveBigIntegerField(
        'id организации в Яндекс.Картах',
        null=True,
        blank=True,
        help_text='Для виджета отзывов: число из адреса карточки, '
        'yandex.by/maps/org/…/141315425329/. Пусто — вместо виджета '
        'только ссылка на карту',
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
            f'MP4 (H.264), до {MAX_VIDEO_MB} МБ: до 3–4 минут в 1080p. '
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
    IMAGE_HINT = (
        (
            'Вертикальное: рамка 4:5 везде — главная, «Проекты», товар; '
            'от 1080 px по ширине'
        ),
        1080,
    )

    title = models.CharField(
        'название',
        max_length=150,
    )
    place = models.CharField(
        'место',
        max_length=150,
        blank=True,
        help_text='Адрес или объект: «Минск, ул. Нововиленская, 57». '
        'Пусто — на сайте только название',
    )
    series = models.ManyToManyField(
        'catalog.Series',
        verbose_name='серии',
        related_name='projects',
        blank=True,
    )
    video = models.FileField(
        'видео',
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
            'На сайте — вторым кадром в галерее проекта, после главного фото'
        ),
    )

    class Meta(Sortable.Meta):
        verbose_name = 'проект'
        verbose_name_plural = 'проекты'

    def __str__(self):
        return self.title


class ProjectPhoto(WithImage, Sortable):
    """Дополнительные фото проекта: на сайте листаются в галерее поверх списка."""

    cache_tag = Tag.PROJECTS
    IMAGE_HINT = (
        'Любой формы — в галерее показывается целиком; от 1080 px',
        1080,
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='photos',
    )

    class Meta(Sortable.Meta):
        verbose_name = 'фото проекта'
        verbose_name_plural = 'ещё фото'

    def default_alt(self) -> str:
        return self.project.title

    def __str__(self):
        return self.alt


class Article(WithImage):
    """Заголовок, фото и текст из редактора — общее у статьи и акции.
    Обе на странице «Блог и акции», поэтому и тег кэша один."""

    cache_tag = Tag.POSTS

    title = models.CharField(
        'заголовок',
        max_length=200,
    )
    body = models.TextField(
        'текст',
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.body = clean_html(self.body)
        super().save(*args, **kwargs)


class Post(Published, Article):
    IMAGE_HINT = ('Горизонтальное 16:9, от 1600 px по ширине', 1600)

    published_at = models.DateField(
        'дата',
        default=timezone.localdate,
    )
    lead = models.TextField(
        'лид',
        help_text='Пара предложений под заголовком и в списке статей',
    )

    class Meta:
        verbose_name = 'статья'
        verbose_name_plural = 'блог'
        ordering = ['-published_at', '-pk']

    @property
    def read_minutes(self):
        return read_minutes(self.body)


class PromoQuerySet(models.QuerySet):
    def active(self):
        """На сайте: включённые, бессрочные или срок ещё не кончился."""
        return self.filter(
            models.Q(ends_at__isnull=True)
            | models.Q(ends_at__gte=timezone.localdate()),
            is_published=True,
        )


class Promo(Article, Sortable):
    """Акция: своей страницы нет, весь текст — в карточке на «Блог и акции»."""

    # Карточки акций — готовые картинки поставщиков, часто вертикальные:
    # на сайте рамка по их форме (решение 150), поэтому без порога ширины
    IMAGE_HINT = ('Любая форма, на сайте — целиком, без обрезки', 0)

    ends_at = models.DateField(
        'действует до',
        null=True,
        blank=True,
        help_text='Включительно. Пусто — бессрочная. После даты акция '
        'пропадёт с сайта сама',
    )
    is_published = models.BooleanField(
        'на сайте',
        default=True,
    )

    objects = PromoQuerySet.as_manager()

    class Meta(Sortable.Meta):
        verbose_name = 'акция'
        verbose_name_plural = 'акции'


class ShowroomPhoto(WithImage, Sortable):
    cache_tag = Tag.SHOWROOM
    IMAGE_HINT = ('Горизонтальное 3:2, от 1600 px по ширине', 1600)

    class Meta(Sortable.Meta):
        verbose_name = 'фото шоурума'
        verbose_name_plural = 'шоурум'

    def default_alt(self) -> str:
        return 'Зал шоурума АртТепло'

    def __str__(self):
        return self.alt
