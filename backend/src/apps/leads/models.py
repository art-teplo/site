from django.conf import settings
from django.core.files.storage import storages
from django.core.validators import FileExtensionValidator
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

from apps.core.utils import (
    AutoUploadTo,
    FileSignatureValidator,
    FileSizeValidator,
    SizeUnit,
)

from .sources import is_product, source_label

# Лимит Bot API на отправку файла
MAX_FILE_MB = 50

# Расширение → допустимые начала файла
FILE_SIGNATURES = {
    'pdf': (b'%PDF',),
    'jpg': (b'\xff\xd8\xff',),
    'jpeg': (b'\xff\xd8\xff',),
    'png': (b'\x89PNG\r\n\x1a\n',),
    'xlsx': (b'PK\x03\x04',),
    'xls': (b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',),
}


def private_storage():
    return storages['private']


class Lead(models.Model):
    """Заявка с сайта. Единственное, что сайт пишет в базу."""

    class ContactMethod(models.TextChoices):
        CALL = 'call', 'Звонок'
        VIBER = 'viber', 'Viber'
        TELEGRAM = 'telegram', 'Telegram'

    created_at = models.DateTimeField(
        'создана',
        auto_now_add=True,
    )

    name = models.CharField(
        'имя',
        max_length=100,
    )
    phone = PhoneNumberField(
        'телефон',
        region='BY',
    )
    contact_method = models.CharField(
        'способ связи',
        max_length=16,
        choices=ContactMethod,
        default=ContactMethod.CALL,
    )
    comment = models.TextField(
        'комментарий',
        blank=True,
    )
    company = models.CharField(
        'студия или компания',
        max_length=150,
        blank=True,
    )
    city = models.CharField(
        'город',
        max_length=100,
        blank=True,
    )
    file = models.FileField(
        'файл',
        storage=private_storage,
        upload_to=AutoUploadTo('file'),
        max_length=200,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=list(FILE_SIGNATURES),
                message='Подойдут PDF, JPG, PNG или Excel',
            ),
            FileSizeValidator(MAX_FILE_MB, SizeUnit.MiB),
            FileSignatureValidator(FILE_SIGNATURES),
        ],
    )
    file_name = models.CharField(
        'имя файла',
        max_length=255,
        blank=True,
    )

    # Откуда пришла: quiz, home:paths, series/<slug>, catalog/<slug> …; контекст — ответы
    # квиза или товар с вариантом
    source = models.CharField(
        'источник',
        max_length=64,
    )
    page = models.CharField(
        'страница',
        max_length=300,
        blank=True,
    )
    context = models.TextField(
        'контекст',
        blank=True,
    )

    # Закон РБ № 99-З: оператор обязан доказать, что согласие было
    consent_at = models.DateTimeField(
        'согласие: время',
    )
    consent_ip = models.GenericIPAddressField(
        'согласие: IP',
        null=True,
    )
    consent_version = models.CharField(
        'согласие: версия текста',
        max_length=32,
    )

    tg_chat_id = models.BigIntegerField(
        'Telegram: чат',
        null=True,
        blank=True,
    )
    tg_message_id = models.BigIntegerField(
        'Telegram: сообщение',
        null=True,
        blank=True,
    )
    tg_file_sent = models.BooleanField(
        'Telegram: файл отправлен',
        default=False,
    )

    # Кто взял кнопкой «Беру» в группе
    assignee_tg_id = models.BigIntegerField(
        'ответственный: id в Telegram',
        null=True,
        blank=True,
    )
    assignee_name = models.CharField(
        'ответственный',
        max_length=150,
        blank=True,
    )
    assigned_at = models.DateTimeField(
        'взята',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'заявка'
        verbose_name_plural = 'заявки'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'Заявка № {self.pk}'

    @property
    def source_label(self):
        return source_label(self.source)

    @property
    def is_product(self):
        return is_product(self.source)

    @property
    def page_url(self):
        # Домен — из настроек: адрес целиком присылает браузер, и так
        # в чат менеджеров можно было бы подсунуть чужую ссылку
        page = self.page
        if not settings.SITE_URL or not page.startswith('/'):
            return ''
        if page.startswith('//'):  # //evil.example — чужой домен
            return ''
        return f'{settings.SITE_URL}{page}'
