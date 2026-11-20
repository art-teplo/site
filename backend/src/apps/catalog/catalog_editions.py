"""Read-only план и атомарное разделение подтверждённых исполнений прайса."""

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from django.db import transaction

from apps.content.models import Project, Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend

from . import serializers
from .importers.factory_editions import edition_for_row, registry
from .importers.factory_photos import confirmed_photo_target
from .importers.parse import parse_row
from .importers.product_families import assign_family
from .importers.xlsx import _open, read_rows
from .kzto_split import _clone_fields
from .models import (
    ColorGroup,
    Series,
    SeriesFile,
    SeriesImage,
    Showcase,
    Variant,
)

GEOMETRY = ('height_mm', 'width_mm', 'depth_mm', 'power_w')


@dataclass
class EditionPlan:
    source: str
    source_sha256: str
    parents: list[int]
    fingerprint: str
    moves: list[dict] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    inventory: list[dict] = field(default_factory=list)
    exceptions: list[dict] = field(default_factory=list)


def _digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()


def _fingerprint(parents):
    series = Series.objects.filter(pk__in=parents)
    targets = [
        t['slug']
        for s in series
        for t in registry()['parents'][s.slug]['targets'].values()
    ]
    ids = (
        list(
            Series.objects.filter(slug__in=targets).values_list(
                'pk', flat=True
            )
        )
        + parents
    )
    groups = ColorGroup.objects.filter(series_id__in=ids)
    variants = Variant.objects.filter(series_id__in=ids)
    models = [
        series,
        Series.objects.filter(slug__in=targets),
        groups,
        variants,
        SeriesImage.objects.filter(series_id__in=ids),
        SeriesFile.objects.filter(series_id__in=ids),
        Project.series.through.objects.filter(series_id__in=ids),
        Showcase.objects.filter(series_id__in=ids),
        Variant.color_groups.through.objects.filter(
            variant_id__in=variants.values('pk')
        ),
        ColorGroup.colors.through.objects.filter(
            colorgroup_id__in=groups.values('pk')
        ),
    ]
    return _digest([list(q.order_by('pk').values()) for q in models])


def _source_rows(source, brands):
    book = _open(source)
    try:
        if 'guardo' in brands:
            for row in read_rows(book['Guardo']):
                parsed = parse_row(row)
                if parsed and parsed.series_slug in registry()['parents']:
                    yield parsed
        if 'velar' in brands:
            from .importers.velar import SHEETS, Summary, parse_sheet  # noqa: PLC0415

            summary = Summary()
            for title in book.sheetnames:
                if title in SHEETS:
                    rows, _ = parse_sheet(
                        title, book[title].iter_rows(values_only=True), summary
                    )
                    yield from rows
    finally:
        book.close()


@lru_cache(maxsize=2)
def _source_index(source, source_hash, brands):
    cache_key = _digest((source_hash, brands, registry(), 'source-adapter-v1'))
    cache_dir = (
        Path(tempfile.gettempdir())
        / f'art-teplo-source-witnesses-{os.getuid()}'
    )
    cache_dir.mkdir(mode=0o700, exist_ok=True)
    if (
        cache_dir.is_symlink()
        or cache_dir.stat().st_uid != os.getuid()
        or cache_dir.stat().st_mode & 0o077
    ):
        message = 'Небезопасный каталог кэша исходников'
        raise ValueError(message)
    cache_path = cache_dir / f'art-teplo-edition-witnesses-{cache_key}.json'
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        return {tuple(k): v for k, v in cached['records']}, cached['conflicts']
    index = {}
    conflicts = []
    for row in _source_rows(source, brands):
        try:
            target = edition_for_row(row)
        except ValueError as error:
            conflicts.append(
                {
                    'series': row.series_slug
                    if hasattr(row, 'series_slug')
                    else row.sheet.slug,
                    'message': str(error),
                }
            )
            continue
        if not target:
            continue
        values = (
            row.values
            if hasattr(row, 'sheet')
            else {k: getattr(row, k) for k in GEOMETRY}
        )
        article = row.article if hasattr(row, 'sheet') else row.base_article
        key = (
            target['parent'],
            article,
            row.connection,
            *(values.get(k) for k in GEOMETRY),
        )
        known = index.get(key)
        if known and known != target:
            conflicts.append(
                {
                    'series': target['parent'],
                    'message': f'Неоднозначный источник {article}',
                }
            )
        index[key] = target
    cache_path.write_text(
        json.dumps(
            {'records': list(index.items()), 'conflicts': conflicts},
            ensure_ascii=False,
        )
    )
    return index, conflicts


def plan_catalog_editions(
    *, source: Path, series_slugs: list[str] | None = None
):
    source = Path(source)
    entries = registry()['parents']
    chosen = series_slugs or list(entries)
    unknown = set(chosen) - entries.keys()
    if unknown:
        message = f'Неизвестные серии: {sorted(unknown)}'
        raise ValueError(message)
    parents = list(
        Series.objects.filter(slug__in=chosen).select_related(
            'brand', 'category'
        )
    )
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    index, source_conflicts = (
        _source_index(
            str(source),
            source_hash,
            tuple(sorted({s.brand.slug for s in parents})),
        )
        if parents
        else ({}, [])
    )
    conflicts = [
        c['message'] for c in source_conflicts if c['series'] in chosen
    ]
    ids = [s.pk for s in parents]
    plan = EditionPlan(
        str(source),
        hashlib.sha256(source.read_bytes()).hexdigest(),
        ids,
        _fingerprint(ids),
        conflicts=conflicts,
        exceptions=registry()['exceptions'],
    )
    existing_targets = {
        s.slug: s
        for s in Series.objects.filter(
            slug__in=[
                t['slug']
                for p in parents
                for t in entries[p.slug]['targets'].values()
            ]
        )
    }
    for old in parents:
        if (
            old.brand.slug != entries[old.slug]['brand']
            or old.category.slug != 'radiatory'
        ):
            plan.conflicts.append(f'Бренд/категория: {old.slug}')
            continue
        group_names = list(old.color_groups.values_list('name', flat=True))
        if len(group_names) != len(set(group_names)):
            plan.conflicts.append(f'Неоднозначные группы цветов: {old.slug}')
        plan.inventory.append(
            {
                'parent': old.slug,
                'groups': group_names,
                'showcases': list(old.showcases.values_list('pk', flat=True)),
                'projects': list(old.projects.values_list('pk', flat=True)),
                'images': list(old.images.values_list('pk', flat=True)),
                'files': list(old.files.values_list('pk', flat=True)),
            }
        )
        for variant in old.variants.prefetch_related('color_groups'):
            key = (
                old.slug,
                variant.article,
                variant.connection,
                *(getattr(variant, k) for k in GEOMETRY),
            )
            target = index.get(key)
            if target is None:
                plan.conflicts.append(
                    f'Нет точного подтверждения: {old.slug}, {variant.pk}, {variant.article}, {variant.connection}'
                )
                continue
            existing = existing_targets.get(target['slug'])
            if existing and (
                existing.brand_id != old.brand_id
                or existing.category_id != old.category_id
                or existing.factory_orientation != target['orientation']
                or existing.markup_percent != old.markup_percent
                or existing.variants.filter(
                    article=variant.article, connection=variant.connection
                ).exists()
            ):
                plan.conflicts.append(
                    f'Конфликт целевой серии: {target["slug"]}, {variant.article}'
                )
            plan.moves.append(
                {
                    'variant_id': variant.pk,
                    'old_id': old.pk,
                    'target': target['slug'],
                    'orientation': target['orientation'],
                    'article': variant.article,
                    'connection': variant.connection,
                    'geometry': {k: getattr(variant, k) for k in GEOMETRY},
                    'groups': [g.pk for g in variant.color_groups.all()],
                }
            )
    return plan


def _pin_showcase(showcase, old):
    if showcase.image:
        return
    photo = serializers._card_photo(showcase, old)  # noqa: SLF001
    if photo:
        Showcase.objects.filter(pk=showcase.pk).update(
            image=photo.image.name,
            image_width=photo.image_width,
            image_height=photo.image_height,
            image_focus=photo.image_focus,
            image_alt=photo.alt,
        )


def _copy_groups(old, new):
    groups = {}
    for g in old.color_groups.all():
        copied = new.color_groups.filter(name=g.name).first()
        if copied is None:
            copied = ColorGroup.objects.create(
                series=new,
                legacy_origin=g,
                **_clone_fields(g, {'series', 'legacy_origin'}),
            )
            copied.colors.set(g.colors.all())
        elif any(
            getattr(copied, k) != getattr(g, k)
            for k in ('percent', 'any_ral', 'is_base')
        ) or set(copied.colors.values_list('pk', flat=True)) != set(
            g.colors.values_list('pk', flat=True)
        ):
            message = (
                f'Группа цветов целевой серии отличается: {new.slug}, {g.name}'
            )
            raise ValueError(message)
        if copied.legacy_origin_id not in (None, g.pk):
            message = f'Другая исходная группа цветов: {new.slug}, {g.name}'
            raise ValueError(message)
        if copied.legacy_origin_id is None:
            copied.legacy_origin = g
            copied.save(update_fields=['legacy_origin'])
        groups[new.slug, g.pk] = copied.pk
    return groups


def _create_targets(old):
    assign_family(old)
    photo = serializers._main_image(old)  # noqa: SLF001
    if photo and not old.family.presentation_photo_id:
        old.family.presentation_photo = photo
        old.family.save(update_fields=['presentation_photo'])
    for showcase in old.showcases.select_related('variant'):
        _pin_showcase(showcase, old)
    destinations = {}
    group_map = {}
    for target in registry()['parents'][old.slug]['targets'].values():
        new, created = Series.objects.get_or_create(
            slug=target['slug'],
            defaults={
                **_clone_fields(
                    old,
                    {
                        'slug',
                        'name',
                        'factory_orientation',
                        'video',
                        'video_poster',
                    },
                ),
                'name': target['name'],
                'factory_orientation': target['orientation'],
            },
        )
        if not created and new.markup_percent != old.markup_percent:
            message = f'Наценка целевой серии отличается: {new.slug}'
            raise ValueError(message)
        destinations[new.slug] = new
        group_map.update(_copy_groups(old, new))
        # Только явно размеченные фото своего исполнения. Объекты storage переиспользуются.
        for image in old.images.all():
            if (
                confirmed_photo_target(image, new)
                and not new.images.filter(image=image.image.name).exists()
            ):
                SeriesImage.objects.create(
                    series=new, **_clone_fields(image, {'series'})
                )
    return destinations, group_map


def apply_catalog_editions(plan):
    if plan.conflicts:
        message = 'Перенос отклонён: ' + '; '.join(plan.conflicts[:5])
        raise ValueError(message)
    with muted_revalidation(), transaction.atomic():
        list(Series.objects.select_for_update().filter(pk__in=plan.parents))
        list(
            Variant.objects.select_for_update().filter(
                series_id__in=plan.parents
            )
        )
        if (
            _fingerprint(plan.parents) != plan.fingerprint
            or hashlib.sha256(Path(plan.source).read_bytes()).hexdigest()
            != plan.source_sha256
        ):
            message = 'Данные или источник изменились после проверки; постройте план заново'
            raise ValueError(message)
        destinations, groups = {}, {}
        active_parents = {m['old_id'] for m in plan.moves}
        for old in (
            Series.objects.filter(pk__in=active_parents)
            .select_related('brand', 'category', 'family')
            .prefetch_related('images')
        ):
            targets, mapping = _create_targets(old)
            destinations.update(targets)
            groups.update(mapping)
            for move in (m for m in plan.moves if m['old_id'] == old.pk):
                Variant.objects.filter(pk=move['variant_id']).update(
                    series=destinations[move['target']],
                    orientation=move['orientation'],
                )
                variant = Variant.objects.get(pk=move['variant_id'])
                variant.color_groups.set(
                    [groups[move['target'], pk] for pk in move['groups']]
                )
                Showcase.objects.filter(series=old, variant=variant).update(
                    series=destinations[move['target']]
                )
            # Общая витрина без артикула остаётся у линейки; презентационные фото уже закреплены.
            for new in targets.values():
                if not new.showcases.exists():
                    photo = old.family.presentation_photo
                    showcase = Showcase.objects.create(
                        series=new,
                        label='Вертикальный'
                        if new.factory_orientation == 'v'
                        else 'Горизонтальный',
                    )
                    if photo:
                        Showcase.objects.filter(pk=showcase.pk).update(
                            image=photo.image.name,
                            image_width=photo.image_width,
                            image_height=photo.image_height,
                            image_focus=photo.image_focus,
                            image_alt=photo.alt,
                        )
            Series.objects.filter(pk=old.pk).update(is_published=False)
        if plan.moves:
            transaction.on_commit(
                lambda: revalidate_frontend.delay(Tag.CATALOG)
            )
    return {
        'moved': len(plan.moves),
        'series': sorted(destinations),
        'archived': len(active_parents),
    }
