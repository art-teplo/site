# ruff: noqa: PLC0415, SLF001
import io

import pytest
from django.core.files.storage import FileSystemStorage
from PIL import Image

from apps.catalog.models import (
    Brand,
    Category,
    Series,
    SeriesFile,
    SeriesImage,
)


@pytest.fixture
def media_targets(db, tmp_path, monkeypatch):  # noqa: ARG001
    storage = FileSystemStorage(location=tmp_path / 'media')
    for model, field in [(SeriesFile, 'file'), (SeriesImage, 'image')]:
        monkeypatch.setattr(model._meta.get_field(field), 'storage', storage)
    brand = Brand.objects.create(slug='velar', name='Velar')
    cat = Category.objects.create(slug='radiatory', name='Радиаторы')
    return [
        Series.objects.create(
            brand=brand,
            category=cat,
            slug=f'velar-p30-{o}',
            name=f'P30 {o}',
            factory_orientation=o,
        )
        for o in ['h', 'v']
    ]


@pytest.mark.django_db
def test_shared_document_downloaded_once_hidden_and_manual_materials_preserved(
    media_targets,
):
    from apps.catalog.importers.catalog_media import sync_catalog_media

    h, v = media_targets
    manual = SeriesFile.objects.create(
        series=h, title='Ручной', file='manual.pdf'
    )
    sources = [
        {
            'series': s.slug,
            'files': [
                {
                    'url': 'https://factory.test/p.pdf',
                    'filename': 'p.pdf',
                    'title': 'Паспорт',
                }
            ],
            'photos': [],
        }
        for s in [h, v]
    ]
    calls = []

    def fetch(url):
        calls.append(url)
        return b'%PDF-1.4\n%%EOF'

    report = sync_catalog_media(sources, apply=True, fetcher=fetch)
    assert not report['errors']
    assert len(calls) == 1
    files = list(SeriesFile.objects.exclude(pk=manual.pk))
    assert len(files) == 2
    assert files[0].file.name == files[1].file.name
    files[0].is_visible = False
    files[0].save()
    sync_catalog_media(
        sources, apply=True, fetcher=lambda _: pytest.fail('Already present')
    )
    assert not SeriesFile.objects.get(pk=files[0].pk).is_visible
    assert SeriesFile.objects.filter(pk=manual.pk).exists()


@pytest.mark.django_db
def test_bad_document_network_failure_and_wrong_orientation_create_no_bad_rows(
    media_targets,
):
    from apps.catalog.importers.catalog_media import sync_catalog_media

    h, _ = media_targets

    def failed(_):
        message = 'network'
        raise OSError(message)

    row = {
        'series': h.slug,
        'files': [
            {
                'url': 'https://factory.test/x.pdf',
                'filename': 'x.pdf',
                'title': 'bad',
            }
        ],
        'photos': [],
    }
    for fetch in [lambda _: b'<html>error</html>', failed]:
        assert sync_catalog_media([row], apply=True, fetcher=fetch)['errors']
        assert not h.files.exists()
    row['photos'] = [
        {
            'url': 'https://factory.test/v.jpg',
            'orientation': 'v',
            'kind': 'product',
        }
    ]
    row['files'] = []
    assert sync_catalog_media([row], apply=True, fetcher=failed)['errors']
    assert not h.images.exists()


@pytest.mark.django_db
def test_photo_metadata_and_hidden_visibility_are_stable_on_resync(
    media_targets,
):
    from apps.catalog.importers.catalog_media import sync_catalog_media

    h, _ = media_targets
    data = io.BytesIO()
    Image.new('RGB', (80, 60), 'black').save(data, 'JPEG')
    row = {
        'series': h.slug,
        'photos': [
            {
                'url': 'https://factory.test/h.jpg',
                'orientation': 'h',
                'kind': 'product',
            }
        ],
        'files': [],
    }
    assert not sync_catalog_media(
        [row], apply=False, fetcher=lambda _: pytest.fail('Dry run')
    )['errors']
    assert not h.images.exists()
    sync_catalog_media([row], apply=True, fetcher=lambda _: data.getvalue())
    image = h.images.get()
    assert (image.image_width, image.image_height) == (80, 60)
    image.is_visible = False
    image.save()
    sync_catalog_media(
        [row], apply=True, fetcher=lambda _: pytest.fail('Already present')
    )
    assert not h.images.get().is_visible


@pytest.mark.django_db
def test_photo_digest_mismatch_rejects_file(media_targets):
    from apps.catalog.importers.catalog_media import sync_catalog_media

    h, _ = media_targets
    image = io.BytesIO()
    Image.new('RGB', (10, 10), 'black').save(image, 'JPEG')
    row = {
        'series': h.slug,
        'photos': [
            {
                'url': 'https://factory.test/changed.jpg',
                'orientation': 'h',
                'sha256': '0' * 64,
            }
        ],
        'files': [],
    }
    assert sync_catalog_media(
        [row], apply=True, fetcher=lambda _: image.getvalue()
    )['errors']
    assert not h.images.exists()


@pytest.mark.django_db
@pytest.mark.parametrize('collection', ['photos', 'files'])
def test_source_alias_cannot_republish_hidden_content(
    media_targets, collection
):
    from apps.catalog.importers.catalog_media import sync_catalog_media

    h, _ = media_targets
    if collection == 'photos':
        data = io.BytesIO()
        Image.new('RGB', (20, 20), 'black').save(data, 'JPEG')
        blob = data.getvalue()
        source = {
            'url': 'https://factory.test/original.jpg',
            'orientation': 'h',
            'kind': 'product',
        }
        manager = h.images
    else:
        blob = b'%PDF-1.4\n%%EOF'
        source = {
            'url': 'https://factory.test/original.pdf',
            'filename': 'p.pdf',
            'title': 'Паспорт',
        }
        manager = h.files
    row = {'series': h.slug, collection: [source]}
    sync_catalog_media([row], apply=True, fetcher=lambda _: blob)
    item = manager.get()
    item.is_visible = False
    item.save()
    alias = {**source, 'url': source['url'].replace('original', 'alias')}
    sync_catalog_media(
        [{'series': h.slug, collection: [alias]}],
        apply=True,
        fetcher=lambda _: blob,
    )
    assert manager.count() == 1
    assert not manager.get().is_visible
    repeat = sync_catalog_media(
        [{'series': h.slug, collection: [alias]}],
        apply=True,
        fetcher=lambda _: pytest.fail('Known alias must not download'),
    )
    assert repeat['existing'] == 1
