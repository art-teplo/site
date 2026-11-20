"""Локально созданные публичные медиа при разработке рядом с S3."""

from django.core.files.storage import FileSystemStorage
from storages.backends.s3 import S3Storage

LOCAL_MEDIA_PREFIX = 'local/'


class DevelopmentPublicStorage(S3Storage):
    def __init__(self, **options):
        super().__init__(**options)
        self.local = FileSystemStorage()

    def _storage(self, name):
        return self.local if name.startswith(LOCAL_MEDIA_PREFIX) else super()

    def _open(self, name, mode='rb'):
        return self._storage(name)._open(name, mode)  # noqa: SLF001

    def _save(self, name, content):
        return self._storage(name)._save(name, content)  # noqa: SLF001

    def delete(self, name):
        return self._storage(name).delete(name)

    def exists(self, name):
        return self._storage(name).exists(name)

    def size(self, name):
        return self._storage(name).size(name)

    def url(self, name, parameters=None, expire=None, http_method=None):
        if name.startswith(LOCAL_MEDIA_PREFIX):
            return self.local.url(name)
        return super().url(name, parameters, expire, http_method)

    def get_modified_time(self, name):
        return self._storage(name).get_modified_time(name)
