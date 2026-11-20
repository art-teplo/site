"""Перенос материалов и старых ссылок до удаления архивной серии."""

import re
from copy import copy

from django.db.models import Q

from apps.content.models import Project

from .catalog_cleanup import cleanup_targets
from .importers.factory_photos import confirmed_photo_target
from .importers.product_families import radimax_legacy_targets
from .models import (
    LegacyColorAlias,
    ProductFamily,
    Series,
    SeriesImage,
)


def targets():
    return {**cleanup_targets(), **radimax_legacy_targets()}


def destinations(parent):
    slugs = targets().get(parent.slug, [])
    children = list(
        Series.objects.filter(
            slug__in=slugs,
            brand=parent.brand,
            category=parent.category,
            is_published=True,
            variants__is_active=True,
        )
        .order_by('pk')
        .distinct()
    )
    if not slugs or len(children) != len(slugs) or parent.is_published:
        msg = f'{parent.slug}: не подтверждены все опубликованные замены'
        raise ValueError(msg)
    if (
        parent.variants.exists()
        or parent.connection_options.exists()
        or parent.showcases.exists()
    ):
        msg = f'{parent.slug}: у архива остались варианты, правила или витрина'
        raise ValueError(msg)
    return children


def _clone(row, series):
    item = copy(row)
    item._state = copy(row._state)  # noqa: SLF001
    item.pk = None
    item.series = series
    return item


def _transfer_colors(parent, children):
    count = 0
    for old in parent.color_groups.all():
        old_colors = set(old.colors.all())
        for child in children:
            group = child.color_groups.filter(legacy_origin=old).first()
            if group is None:
                group = child.color_groups.filter(
                    name=old.name, any_ral=old.any_ral
                ).first()
            if group is None:
                group = _clone(old, child)
                group.legacy_origin = None
                if (
                    group.is_base
                    and child.color_groups.filter(is_base=True).exists()
                ):
                    group.is_base = False
                group.save()
            assigned = {
                color
                for other in child.color_groups.exclude(
                    pk=group.pk
                ).prefetch_related('colors')
                for color in other.colors.all()
            }
            group.colors.add(*(old_colors - assigned))
            LegacyColorAlias.objects.get_or_create(
                parent_slug=parent.slug, old_group_id=old.pk, group=group
            )
            if group.legacy_origin_id == old.pk:
                group.legacy_origin = None
                group.save(update_fields=['legacy_origin'])
            count += 1
    return count


def _media_targets(parent, children, row):
    if isinstance(row, SeriesImage):
        confirmed = [
            child for child in children if confirmed_photo_target(row, child)
        ]
        if confirmed:
            return confirmed
    elif parent.brand.slug == 'kzto':
        match = re.search(r'\b(?:NEO\s+)?\d+([HV])\b', row.title, re.I)
        if match:
            return [
                child
                for child in children
                if child.factory_orientation == match.group(1).lower()
            ]
    if parent.brand.slug != 'radimax':
        return children
    label = row.image_alt if isinstance(row, SeriesImage) else row.title
    for child in children:
        attrs = child.variants.values_list('attrs', flat=True).first() or {}
        model = attrs.get('factory_model', '').replace('SOUL', 'Соул')
        if model and re.search(
            rf'(?<!\w){re.escape(model)}(?![\w/])', label, re.I
        ):
            return [child]
    return children


def _transfer_media(parent, children, row, field):
    blob = getattr(row, field).name
    model = type(row)
    family_links = (
        ProductFamily.objects.filter(presentation_photo=row)
        if field == 'image'
        else ProductFamily.objects.none()
    )
    replacements = []
    for child in _media_targets(parent, children, row):
        same = Q(**{field: blob})
        if row.source_sha256:
            same |= Q(source_sha256=row.source_sha256)
        copies = model.objects.filter(series=child)
        item = copies.filter(same).first()
        if item is None:
            item = _clone(row, child)
            if (
                item.source_url
                and copies.filter(source_url=item.source_url).exists()
            ):
                item.source_aliases = list(
                    dict.fromkeys([*item.source_aliases, item.source_url])
                )
                item.source_url = ''
            # Сохраняем отбор Радимакс и не показываем неподтверждённое исполнение в H/V.
            if field == 'image' and (
                parent.brand.slug == 'radimax'
                or (
                    not confirmed_photo_target(row, child)
                    and (
                        child.factory_orientation
                        or item.kind != SeriesImage.Kind.INTERIOR
                    )
                )
            ):
                item.is_visible = False
            item.save()
        replacements.append(item)
    if not replacements:
        msg = f'{parent.slug}: нет назначения для материала {row.pk}'
        raise ValueError(msg)
    if family_links.exists():
        item = replacements[0]
        if (
            item.image_focus != row.image_focus
            or item.image_alt != row.image_alt
        ):
            item = _clone(row, item.series)
            item.source_url = ''
            item.is_visible = False
            item.save()
        family_links.update(presentation_photo=item)
    return len(replacements)


def transfer_archive(parent):
    children = destinations(parent)
    data = {
        'slug': parent.slug,
        'targets': [child.slug for child in children],
        'color_links': _transfer_colors(parent, children),
        'photos': sum(
            _transfer_media(parent, children, row, 'image')
            for row in parent.images.all()
        ),
        'files': sum(
            _transfer_media(parent, children, row, 'file')
            for row in parent.files.all()
        ),
        'projects': list(parent.projects.values_list('pk', flat=True)),
        'video': bool(parent.video),
    }
    projects = Project.objects.filter(pk__in=data['projects'])
    for child in children:
        updates = {}
        if parent.video:
            if child.video and child.video.name != parent.video.name:
                msg = f'{child.slug}: конфликт видео'
                raise ValueError(msg)
            if not child.video:
                updates['video'] = parent.video.name
        if parent.description and not child.description:
            updates['description'] = parent.description
        if updates:
            Series.objects.filter(pk=child.pk).update(**updates)
        for project in projects:
            project.series.add(child)
    parent.delete()
    return data
