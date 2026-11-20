import hashlib
import io
import json
import zipfile

import pytest
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command
from PIL import Image

from apps.catalog.importers import kzto, kzto_media
from apps.catalog.importers.kzto_media import sync_kzto_media
from apps.catalog.importers.kzto_page import Document, Page
from apps.catalog.models import (
    Brand,
    Category,
    Series,
    SeriesFile,
    SeriesImage,
)
from apps.content.tasks import revalidate_frontend


@pytest.fixture
def media_series(tmp_path, monkeypatch):
    storage = FileSystemStorage(location=tmp_path / 'media')
    for model, field in ((SeriesImage, 'image'), (SeriesFile, 'file')):
        monkeypatch.setattr(model._meta.get_field(field), 'storage', storage)  # noqa: SLF001
    brand = Brand.objects.create(slug='kzto', name='КЗТО')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    return Series.objects.create(
        slug='kzto-neo-v', name='NEO V', brand=brand, category=category
    )


@pytest.mark.django_db
def test_sync_keeps_all_photos_and_documents_without_duplicates(media_series):
    photo = io.BytesIO()
    Image.new('RGB', (12, 16)).save(photo, 'JPEG')
    xlsx = io.BytesIO()
    with zipfile.ZipFile(xlsx, 'w') as z:
        z.writestr('[Content_Types].xml', '<Types/>')
        z.writestr('xl/workbook.xml', '<workbook/>')
    page = Page(
        gallery=[f'/p{i}.jpg' for i in range(9)],
        documents=[
            Document('', 'Паспорт', '/p.pdf'),
            Document('', 'Таблица пересчёта', '/t.xlsx'),
        ],
    )
    data = {
        'https://kztoradiator.ru/p.pdf': b'%PDF-1.4\n%%EOF',
        'https://kztoradiator.ru/t.xlsx': xlsx.getvalue(),
    }

    def fetch(url):
        return data.get(url, photo.getvalue())

    sync_kzto_media(media_series, page, fetcher=fetch)
    assert media_series.images.count() == 9
    assert media_series.files.count() == 2
    first = media_series.images.first()
    assert first.image_width == 12
    assert first.image_height == 16
    assert first.source_url.startswith('https://kztoradiator.ru/')
    files = list(media_series.files.values_list('file', flat=True))
    sync_kzto_media(
        media_series,
        page,
        fetcher=lambda _url: pytest.fail('already downloaded'),
    )
    assert media_series.images.count() == 9
    assert list(media_series.files.values_list('file', flat=True)) == files


@pytest.mark.django_db
def test_sync_rejects_html_as_xlsx_and_shares_pdf_storage(media_series):
    page = Page(
        documents=[
            Document('', 'Паспорт', '/p.pdf'),
            Document('', 'Таблица', '/error.xlsx'),
        ]
    )
    report = sync_kzto_media(
        media_series,
        page,
        fetcher=lambda url: (
            b'<html>error</html>' if 'xlsx' in url else b'%PDF-1.4\n%%EOF'
        ),
    )
    assert len(report['errors']) == 1
    second = Series.objects.create(
        slug='kzto-neo-h',
        name='NEO H',
        brand=media_series.brand,
        category=media_series.category,
    )
    sync_kzto_media(
        second,
        Page(documents=page.documents[:1]),
        fetcher=lambda _url: pytest.fail('shared source'),
    )
    assert media_series.files.get().file.name == second.files.get().file.name


@pytest.mark.django_db
def test_media_command_invalidates_once_and_regular_import_uses_same_kinds(
    media_series, tmp_path, monkeypatch, django_capture_on_commit_callbacks
):

    photo = io.BytesIO()
    Image.new('RGB', (12, 16)).save(photo, 'JPEG')
    url = 'https://kztoradiator.ru/known.jpg'
    snapshot = {
        'rows': [
            {
                'series_slug': media_series.slug,
                'gallery': [url],
                'documents': [],
                'description': '',
                'photo_kinds': {url: 'interior'},
            }
        ]
    }
    source = tmp_path / 'inventory.json'
    source.write_text(json.dumps(snapshot))
    (tmp_path / hashlib.sha256(url.encode()).hexdigest()).write_bytes(
        photo.getvalue()
    )
    calls = []
    monkeypatch.setattr(
        revalidate_frontend, 'delay', lambda tag: calls.append(tag)
    )
    with django_capture_on_commit_callbacks(execute=True):
        call_command(
            'sync_kzto_media',
            '--inventory',
            str(source),
            '--cache-dir',
            str(tmp_path),
            '--apply',
        )
    assert calls == ['catalog']
    assert media_series.images.get().kind == 'interior'
    other = Series.objects.create(
        slug='other',
        name='Other',
        brand=media_series.brand,
        category=media_series.category,
    )
    monkeypatch.setattr(
        kzto_media, 'factory_photo_kinds', lambda _slug: {url: 'interior'}
    )
    monkeypatch.setattr(kzto, 'fetch', lambda _url: photo.getvalue())
    result = kzto.SeriesResult(other, False, 0)
    kzto._media(  # noqa: SLF001
        kzto.Summary(), result, [], {other.slug: [Page(gallery=[url])]}
    )
    assert other.images.get().kind == 'interior'
