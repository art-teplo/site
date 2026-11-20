"""Дополнение проверенных материалов: общие объекты, никаких удалений storage."""

import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from PIL import UnidentifiedImageError

from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend
from apps.core.storage import LOCAL_MEDIA_PREFIX

from ..models import MAX_PDF_MB, Series, SeriesFile, SeriesImage
from .kzto import fetch
from .kzto_media import _prepare_image, document_format


def download(url):
    parsed = urlsplit(url)
    if parsed.hostname in ('disk.yandex.ru', 'disk.360.yandex.ru'):
        key = parsed._replace(query='', fragment='').geturl()
        path = parse_qs(parsed.query).get('path', ['/'])[0]
        response = json.loads(
            fetch(
                'https://cloud-api.yandex.net/v1/disk/public/resources/download?'
                + urlencode({'public_key': key, 'path': path})
            )
        )
        return fetch(response['href'])
    return fetch(url)


def _by_source(model, url):
    return model.objects.filter(
        Q(source_url=url) | Q(source_aliases__contains=[url])
    )


def _remember_alias(item, url):
    if url != item.source_url and url not in item.source_aliases:
        type(item).objects.filter(pk=item.pk).update(
            source_aliases=[*item.source_aliases, url]
        )


def _same_content(model, series, digest, url):
    if not digest:
        return False
    existing = (
        model.objects.filter(series=series, source_sha256=digest)
        .order_by('is_visible', 'pk')
        .first()
    )
    if existing:
        _remember_alias(existing, url)
        return True
    return False


def _legacy_document(source):
    legacy = source.get('reuse_file')
    if legacy:
        return SeriesFile.objects.filter(
            series__slug=legacy['series'], title=legacy['title']
        ).first()
    return None


def _save_file(field, filename, data, local_media):
    content = ContentFile(data)
    if local_media:
        name = field.field.generate_filename(field.instance, filename)
        field.name = field.storage.save(f'{LOCAL_MEDIA_PREFIX}{name}', content)
    else:
        field.save(filename, content, save=False)


def _document(series, source, position, fetcher, local_media):
    url = source['url']
    shared = _by_source(SeriesFile, url).first() or _legacy_document(source)
    digest = shared.source_sha256 if shared else ''
    data = None
    if shared is None:
        data = fetcher(url)
        if len(data) > MAX_PDF_MB * 1024 * 1024 or not document_format(
            data, source['filename']
        ):
            message = 'Неверный формат или размер документа'
            raise ValueError(message)
        digest = hashlib.sha256(data).hexdigest()
        if source.get('sha256') and source['sha256'] != digest:
            message = 'Хеш документа отличается от проверенного источника'
            raise ValueError(message)
        shared = SeriesFile.objects.filter(source_sha256=digest).first()
    if _same_content(SeriesFile, series, digest, url):
        return False
    item = SeriesFile(
        series=series,
        source_url=url,
        source_sha256=digest,
        title=source['title'],
        position=position,
    )
    if shared:
        item.file = shared.file.name
    else:
        _save_file(item.file, source['filename'], data, local_media)
    item.save()
    return True


def _image(series, source, position, fetcher, local_media):
    orientation = source.get('orientation', '')
    if (
        series.factory_orientation
        and orientation
        and series.factory_orientation != orientation
    ):
        message = 'Положение фотографии противоречит исполнению'
        raise ValueError(message)
    if source.get('legacy_alt'):
        legacy = series.images.filter(
            image_alt=source['legacy_alt'],
            kind=source['kind'],
        ).first()
        if legacy:
            # Подтверждённый источник старого импортёра, файл и видимость сохраняются.
            if not legacy.source_url:
                SeriesImage.objects.filter(pk=legacy.pk).update(
                    source_url=source['url']
                )
            else:
                _remember_alias(legacy, source['url'])
            return False
    shared = (
        _by_source(SeriesImage, source['url'])
        .exclude(source_sha256='')
        .first()
    )
    digest = shared.source_sha256 if shared else ''
    data = None
    if shared is None:
        data = fetcher(source['url'])
        digest = hashlib.sha256(data).hexdigest()
        if source.get('sha256') and source['sha256'] != digest:
            message = 'Хеш фотографии отличается от проверенного источника'
            raise ValueError(message)
        shared = SeriesImage.objects.filter(source_sha256=digest).first()
    if _same_content(SeriesImage, series, digest, source['url']):
        return False
    item = SeriesImage(
        series=series,
        source_url=source['url'],
        source_sha256=digest,
        kind=source.get('kind', 'product'),
        image_alt=source.get('alt', series.name),
        position=position,
    )
    if shared:
        item.image = shared.image.name
        item.image_width, item.image_height = (
            shared.image_width,
            shared.image_height,
        )
    else:
        data, width, height = _prepare_image(data)
        _save_file(
            item.image,
            source.get('filename', Path(urlsplit(source['url']).path).name),
            data,
            local_media,
        )
        item.image_width, item.image_height = width, height
    color = source.get('color')
    if color:
        from ..models import Color  # noqa: PLC0415

        item.color = Color.objects.filter(code=color).first()
    item.save()
    return True


def sync_catalog_media(
    rows, *, apply=False, fetcher=download, local_media=False
):
    result = {'added_files': 0, 'added_images': 0, 'existing': 0, 'errors': []}
    changed = False
    with muted_revalidation(), transaction.atomic():
        for row in rows:
            series = Series.objects.filter(slug=row['series']).first()
            if not series:
                result['errors'].append(f'Нет исполнения: {row["series"]}')
                continue
            for collection, model, writer, metric in [
                ('files', SeriesFile, _document, 'added_files'),
                ('photos', SeriesImage, _image, 'added_images'),
            ]:
                for position, source in enumerate(
                    row.get(collection, []), start=1
                ):
                    if (
                        _by_source(model, source['url'])
                        .filter(series=series)
                        .exists()
                    ):
                        result['existing'] += 1
                        continue
                    if (
                        collection == 'photos'
                        and series.factory_orientation
                        and source.get('orientation', '')
                        not in ('', series.factory_orientation)
                    ):
                        result['errors'].append(
                            f'{series.slug}: неверное положение {source["url"]}'
                        )
                        continue
                    counter = metric
                    if apply:
                        try:
                            created = writer(
                                series, source, position, fetcher, local_media
                            )
                        except (
                            OSError,
                            ValueError,
                            UnidentifiedImageError,
                            KeyError,
                        ) as error:
                            result['errors'].append(
                                f'{series.slug}, {source["url"]}: {error}'
                            )
                            continue
                        changed = True
                        counter = metric if created else 'existing'
                    result[counter] += 1
        if changed:
            transaction.on_commit(
                lambda: revalidate_frontend.delay(Tag.CATALOG)
            )
    return result
