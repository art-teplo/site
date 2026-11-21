from django.core.files.base import ContentFile
from storages.backends.s3 import S3Storage

from apps.core.storage import DevelopmentPublicStorage


def test_development_public_media_routes_only_local_prefix(
    settings, tmp_path, monkeypatch
):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = '/media/'

    def remote_url(*args):  # noqa: ARG001
        return 'https://bucket.example/remote.jpg'

    monkeypatch.setattr(S3Storage, 'url', remote_url)
    monkeypatch.setattr(S3Storage, 'exists', lambda *_: False)
    storage = DevelopmentPublicStorage()
    name = storage.save('local/preview.jpg', ContentFile(b'local'))
    assert name == 'local/preview.jpg'
    assert storage.url(name) == '/media/local/preview.jpg'
    assert storage.exists(name)
    assert storage.size(name) == 5
    with storage.open(name) as stream:
        assert stream.read() == b'local'
    assert storage.url('remote.jpg') == 'https://bucket.example/remote.jpg'
    storage.delete(name)
    assert not storage.exists(name)


def test_development_media_reads_migrated_local_key_from_s3(
    settings, tmp_path, monkeypatch
):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = '/media/'
    name = 'local/preview.jpg'
    monkeypatch.setattr(
        S3Storage,
        'url',
        lambda _storage, key, *_: f'https://bucket.example/{key}',
    )
    monkeypatch.setattr(S3Storage, 'exists', lambda _, key: key == name)
    monkeypatch.setattr(S3Storage, 'size', lambda _, key: len(key))
    storage = DevelopmentPublicStorage()

    assert storage.url(name) == f'https://bucket.example/{name}'
    assert storage.exists(name)
    assert storage.size(name) == len(name)
