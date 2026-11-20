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
