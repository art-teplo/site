import uuid
from enum import IntEnum, auto
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import models
from django.utils.deconstruct import deconstructible
from rest_framework.throttling import BaseThrottle

# Другие имена JPEG (так сохраняют Windows и браузеры) — в .jpg: по
# расширению хранилище ставит тип файла, а сайт выбирает обработку
SAME_EXTENSIONS = {'.jpeg': '.jpg', '.jfif': '.jpg', '.jpe': '.jpg'}


@deconstructible
class AutoUploadTo:
    """Путь вида <таблица>/<поле>/<uuid>.<расширение>: имя от клиента
    на диск не попадает."""

    def __init__(
        self,
        field_folder: str,
    ):
        self.field_folder = field_folder

    def __call__(self, instance: models.Model, filename: str) -> str:
        db_table = instance._meta.db_table  # noqa: SLF001
        ext = Path(filename).suffix.lower()
        ext = SAME_EXTENSIONS.get(ext, ext)
        unique_name = f'{uuid.uuid4()}{ext}'
        path = Path(db_table) / self.field_folder / unique_name
        return str(path)


class SizeUnit(IntEnum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):  # noqa: ARG004
        return 2 ** (10 * count)

    B = auto()
    KiB = auto()
    MiB = auto()
    GiB = auto()


SIZE_UNIT_LABELS = {
    SizeUnit.B: 'Б',
    SizeUnit.KiB: 'КБ',
    SizeUnit.MiB: 'МБ',
    SizeUnit.GiB: 'ГБ',
}


@deconstructible
class FileSizeValidator:
    message = 'Файл больше %(max_size)s'

    def __init__(
        self,
        max_value: int,
        unit: SizeUnit,
    ) -> None:
        self.max_value = max_value
        self.unit = unit
        self.max_size_bytes = max_value * unit.value

    def __call__(self, file: File) -> None:
        if file.size > self.max_size_bytes:
            raise ValidationError(
                self.message,
                code='file_too_big',
                params={
                    'max_size': (
                        f'{self.max_value} {SIZE_UNIT_LABELS[self.unit]}'
                    ),
                },
            )

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, FileSizeValidator)
            and self.max_value == other.max_value
            and self.unit == other.unit
            and self.message == other.message
        )


@deconstructible
class FileSignatureValidator:
    """Начало файла совпадает с его расширением.

    Расширение и тип из заголовка задаёт клиент — проверяем сами байты.
    Расширения не из списка пропускает: их отсекает FileExtensionValidator.
    """

    message = 'Файл повреждён или не совпадает с расширением'

    def __init__(
        self,
        signatures: dict[str, tuple[bytes, ...]],  # 'pdf' → (b'%PDF',)
    ) -> None:
        self.signatures = signatures

    def __call__(self, file: File) -> None:
        ext = Path(file.name).suffix.lower().removeprefix('.')
        signatures = self.signatures.get(ext)
        if signatures is None:
            return
        file.seek(0)
        head = file.read(max(len(s) for s in signatures))
        file.seek(0)
        if not head.startswith(signatures):
            raise ValidationError(self.message, code='bad_signature')

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, FileSignatureValidator)
            and self.signatures == other.signatures
            and self.message == other.message
        )


def client_ip(request) -> str | None:
    """IP клиента так же, как его видит троттлинг DRF (NUM_PROXIES)."""
    return BaseThrottle().get_ident(request) or None
