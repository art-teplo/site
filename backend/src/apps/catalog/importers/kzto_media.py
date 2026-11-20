"""Дополнение заводских материалов без удаления ручных файлов."""

import hashlib
import io
import json
import zipfile
from functools import cache
from pathlib import Path
from urllib.parse import urlsplit

from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

from apps.content.models import MAX_IMAGE_MB

from ..gallery_curation import hidden_factory_photo
from ..models import MAX_PDF_MB, SeriesFile, SeriesImage
from ..photos import trim_white
from .kzto import _file_name, absolute, fetch

BAD_IMAGE = 'Неверный формат или размер фото'
BAD_DOCUMENT = 'Неверный формат или размер документа'


@cache
def factory_photo_kinds(slug):
    source = (
        Path(__file__).resolve().parents[1] / 'data/kzto_media_sources.json'
    )
    rows = json.loads(source.read_text())['rows']
    return next(
        (r['photo_kinds'] for r in rows if r['series_slug'] == slug), {}
    )


def document_format(data: bytes, url: str) -> bool:
    suffix = urlsplit(url).path.lower()
    if suffix.endswith('.pdf'):
        return data.startswith(b'%PDF-')
    if suffix.endswith('.xlsx'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = set(archive.namelist())
                return {'[Content_Types].xml', 'xl/workbook.xml'} <= names
        except zipfile.BadZipFile:
            return False
    return False


def _prepare_image(data):
    if len(data) > MAX_IMAGE_MB * 1024 * 1024:
        raise ValueError(BAD_IMAGE)
    with Image.open(io.BytesIO(data)) as image:
        image.verify()
    with Image.open(io.BytesIO(data)) as image:
        if image.format not in ('JPEG', 'PNG', 'WEBP'):
            raise ValueError(BAD_IMAGE)
        width, height = image.size
    trimmed = trim_white(data)
    if trimmed:
        return trimmed.data, trimmed.width, trimmed.height
    return data, width, height


def _sync_image(series, source, position, fetcher, kind):
    url = absolute(source)
    shared = (
        SeriesImage.objects.filter(source_url=url)
        .exclude(source_sha256='')
        .first()
    )
    if shared is None:
        data = fetcher(url)
        digest = hashlib.sha256(data).hexdigest()
        shared = SeriesImage.objects.filter(source_sha256=digest).first()
    else:
        digest = shared.source_sha256
    item = SeriesImage(
        series=series,
        source_url=url,
        source_sha256=digest,
        kind=kind,
        is_visible=not hidden_factory_photo(series.slug, url),
        image_alt=f'{series.name} — фото {position}',
        position=position,
    )
    if shared is not None:
        item.image = shared.image.name
        item.image_width, item.image_height = (
            shared.image_width,
            shared.image_height,
        )
    else:
        data, width, height = _prepare_image(data)
        item.image.save(_file_name(url), ContentFile(data), save=False)
        item.image_width, item.image_height = width, height
    item.save()


def _sync_document(series, document, position, fetcher):
    url = absolute(document.url)
    shared = (
        SeriesFile.objects.filter(source_url=url)
        .exclude(source_sha256='')
        .first()
    )
    if shared is None:
        data = fetcher(url)
        if len(data) > MAX_PDF_MB * 1024 * 1024 or not document_format(
            data, url
        ):
            raise ValueError(BAD_DOCUMENT)
        digest = hashlib.sha256(data).hexdigest()
        shared = SeriesFile.objects.filter(source_sha256=digest).first()
    else:
        digest = shared.source_sha256
    item = SeriesFile(
        series=series,
        source_url=url,
        source_sha256=digest,
        title=document.title[:150],
        position=position,
    )
    if shared is not None:
        item.file = shared.file.name
    else:
        item.file.save(_file_name(url), ContentFile(data), save=False)
    item.save()


def _sync_collection(
    series, sources, report, *, dry_run, fetcher, photo_kinds
):
    for position, source in enumerate(sources.gallery, start=1):
        url = absolute(source)
        if series.images.filter(source_url=url).exists():
            report['existing'] += 1
            continue
        try:
            if not dry_run:
                _sync_image(
                    series,
                    source,
                    position,
                    fetcher,
                    photo_kinds.get(source, SeriesImage.Kind.PRODUCT),
                )
            report['images'] += 1
        except (OSError, ValueError, UnidentifiedImageError) as error:
            report['errors'].append(f'{url}: {error}')
    for position, document in enumerate(sources.documents, start=1):
        url = absolute(document.url)
        if (
            not urlsplit(url).path.lower().endswith(('.pdf', '.xlsx'))
            or 'каталог' in document.title.lower()
        ):
            report['additional'].append(url)
            continue
        if series.files.filter(source_url=url).exists():
            report['existing'] += 1
            continue
        try:
            if not dry_run:
                _sync_document(series, document, position, fetcher)
            report['files'] += 1
        except (OSError, ValueError) as error:
            report['errors'].append(f'{url}: {error}')


def sync_kzto_media(
    series, sources, *, dry_run=False, fetcher=None, photo_kinds=None
):
    report = {
        'images': 0,
        'files': 0,
        'existing': 0,
        'errors': [],
        'additional': [],
    }
    _sync_collection(
        series,
        sources,
        report,
        dry_run=dry_run,
        fetcher=fetcher or fetch,
        photo_kinds=photo_kinds or {},
    )
    return report
