import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.validators import FileExtensionValidator
from django.db import connection

from apps.catalog.models import SeriesImage
from apps.content.models import IMAGE_EXTENSIONS
from apps.core.utils import AutoUploadTo


@pytest.mark.django_db
def test_health_ok(client):
    response = client.get('/api/health/')

    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


@pytest.mark.django_db
def test_health_reports_broken_db(client, monkeypatch):
    def broken_cursor():
        raise RuntimeError

    monkeypatch.setattr(connection, 'cursor', broken_cursor)

    response = client.get('/api/health/')

    assert response.status_code == 503
    assert response.json()['db'] == 'error'


@pytest.mark.django_db
def test_admin_on_custom_path(client, settings):
    response = client.get(f'/{settings.ADMIN_PATH}/login/')

    assert response.status_code == 200


@pytest.mark.django_db
def test_schema_closed_for_anonymous(client):
    response = client.get('/api/schema/')

    assert response.status_code == 403


@pytest.mark.parametrize(
    ('filename', 'ext'),
    [
        ('Фото.JFIF', '.jpg'),
        ('photo.jpe', '.jpg'),
        ('photo.JPEG', '.jpg'),
        ('photo.jpg', '.jpg'),
        ('photo.PNG', '.png'),
    ],
)
def test_upload_path_unifies_jpeg_names(filename, ext):
    path = AutoUploadTo('image')(SeriesImage(), filename)

    assert path.startswith('catalog_seriesimage/image/')
    assert path.endswith(ext)
    assert 'Фото' not in path


@pytest.mark.parametrize('name', ['a.jpg', 'b.JFIF', 'c.jpe', 'd.webp'])
def test_image_field_accepts_jpeg_names(name):
    FileExtensionValidator(IMAGE_EXTENSIONS)(SimpleUploadedFile(name, b'x'))
