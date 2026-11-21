"""Локально созданные публичные медиа при разработке рядом с S3."""

from django.core.files.storage import FileSystemStorage
from storages.backends.s3 import S3Storage

LOCAL_MEDIA_PREFIX = 'local/'


class DevelopmentPublicStorage(S3Storage):
    def __init__(self, **options):
        super().__init__(**options)
        self.local = FileSystemStorage()

    def _write_storage(self, name):
        return self.local if name.startswith(LOCAL_MEDIA_PREFIX) else super()

    def _read_storage(self, name):
        if name.startswith(LOCAL_MEDIA_PREFIX) and self.local.exists(name):
            return self.local
        return super()

    def _open(self, name, mode='rb'):
        return self._read_storage(name)._open(name, mode)  # noqa: SLF001

    def _save(self, name, content):
        return self._write_storage(name)._save(name, content)  # noqa: SLF001

    def get_available_name(self, name, max_length=None):
        return self._write_storage(name).get_available_name(name, max_length)

    def delete(self, name):
        return self._write_storage(name).delete(name)

    def exists(self, name):
        return self._read_storage(name).exists(name)

    def size(self, name):
        return self._read_storage(name).size(name)

    def url(self, name, parameters=None, expire=None, http_method=None):
        if self._read_storage(name) is self.local:
            return self.local.url(name)
        return super().url(name, parameters, expire, http_method)

    def get_modified_time(self, name):
        return self._read_storage(name).get_modified_time(name)
