"""Conservative cleanup: retain technical anchors, move media without storage I/O."""

from django.core import serializers

from apps.content.models import Project

from .importers.factory_editions import legacy_targets
from .importers.factory_photos import confirmed_photo_target
from .importers.kzto_series import LEGACY_SERIES
from .models import (
    ColorGroup,
    ConnectionOption,
    ProductFamily,
    Series,
    SeriesFile,
    SeriesImage,
    Showcase,
    Variant,
)
from .serializers import _card_photo


def cleanup_targets():
    return {**LEGACY_SERIES, **legacy_targets()}


def _media_moves(parent, children):
    moves, blockers = [], []
    for model, relation in ((SeriesImage, 'images'), (SeriesFile, 'files')):
        for row in getattr(parent, relation).all():
            candidates = sorted(
                children,
                key=lambda child: (
                    model is SeriesImage
                    and not confirmed_photo_target(row, child)
                ),
            )
            destination = next(
                (
                    child
                    for child in candidates
                    if not row.source_url
                    or not model.objects.filter(
                        series=child, source_url=row.source_url
                    ).exists()
                ),
                None,
            )
            if destination is None:
                blockers.append(f'{relation}:{row.pk}: source URL collision')
                continue
            moves.append(
                {
                    'model': model._meta.label_lower,  # noqa: SLF001
                    'id': row.pk,
                    'series_id': destination.pk,
                    'is_visible': False,
                }
            )
    return moves, blockers


def _parent_plan(parent, targets):
    children = list(Series.objects.filter(slug__in=targets).order_by('pk'))
    dependencies = {
        'variants': list(parent.variants.values_list('pk', flat=True)),
        'connection_options': list(
            parent.connection_options.values_list('pk', flat=True)
        ),
        'color_groups': list(parent.color_groups.values_list('pk', flat=True)),
        'projects': list(parent.projects.values_list('pk', flat=True)),
        'showcases': list(parent.showcases.values_list('pk', flat=True)),
        'family_photo_references': list(
            ProductFamily.objects.filter(
                presentation_photo__series=parent
            ).values_list('pk', flat=True)
        ),
    }
    blockers = [
        name
        for name in (
            'variants',
            'connection_options',
            'color_groups',
            'projects',
            'showcases',
        )
        if dependencies[name]
    ]
    if parent.is_published:
        blockers.append('published')
    if parent.video:
        blockers.append('video')
    if len(children) != len(targets):
        blockers.append('missing children')
    if any(
        child.brand_id != parent.brand_id
        or child.category_id != parent.category_id
        or not child.is_published
        or child.factory_orientation not in ('h', 'v')
        for child in children
    ):
        blockers.append('unconfirmed children')
    moves, media_blockers = _media_moves(parent, children)
    blockers.extend(media_blockers)
    return {
        'id': parent.pk,
        'slug': parent.slug,
        'targets': [child.slug for child in children],
        'status': 'retained' if blockers else 'eligible',
        'blockers': blockers,
        'dependencies': dependencies,
        'media_moves': moves if not blockers else [],
    }


def _nova_plan():
    series = Series.objects.filter(slug='nova-siluet').first()
    if series is None:
        return None
    showcases = list(series.showcases.select_related('variant'))
    if not showcases:
        return {'status': 'retained', 'blockers': ['no existing showcase']}
    keep, *rest = showcases
    photo = keep if keep.image else _card_photo(keep, series)
    if photo is None or not photo.image:
        return {'status': 'retained', 'blockers': ['no existing style photo']}
    updates = {'label': '', 'variant_id': None}
    for field in ('image_width', 'image_height', 'image_focus'):
        updates[field] = getattr(photo, field)
    updates['image'] = photo.image.name
    updates['image_alt'] = (
        keep.image_alt or getattr(photo, 'alt', '') or series.name
    )
    changed = bool(rest) or any(
        (keep.image.name if name == 'image' else getattr(keep, name)) != value
        for name, value in updates.items()
    )
    return {
        'status': 'eligible' if changed else 'unchanged',
        'keep_id': keep.pk,
        'remove_ids': [row.pk for row in rest],
        'updates': updates,
    }


def build_cleanup_report(slugs=None):
    targets = cleanup_targets()
    if slugs and set(slugs) - {*targets, 'nova-siluet'}:
        message = 'Unknown cleanup series'
        raise ValueError(message)
    parents = list(
        Series.objects.filter(slug__in=slugs or targets)
        .order_by('pk')
        .exclude(slug='nova-siluet')
    )
    plans = [_parent_plan(parent, targets[parent.slug]) for parent in parents]
    nova = _nova_plan() if not slugs or 'nova-siluet' in slugs else None
    ids = [parent.pk for parent in parents]
    if nova and nova.get('keep_id'):
        ids.extend(
            Showcase.objects.filter(pk=nova['keep_id']).values_list(
                'series_id', flat=True
            )
        )
    # Native Django serialization records file keys, never reads file bytes.
    backup = []
    for queryset in (
        Series.objects.filter(pk__in=ids),
        SeriesImage.objects.filter(series_id__in=ids),
        SeriesFile.objects.filter(series_id__in=ids),
        Showcase.objects.filter(series_id__in=ids),
        ColorGroup.objects.filter(series_id__in=ids),
        ProductFamily.objects.filter(presentation_photo__series_id__in=ids),
        Project.series.through.objects.filter(series_id__in=ids),
    ):
        backup.extend(serializers.serialize('python', queryset.order_by('pk')))
    return {
        'parents': plans,
        'nova': nova,
        'changes': sum(p['status'] == 'eligible' for p in plans)
        + int(bool(nova and nova['status'] == 'eligible')),
        'backup': backup,
    }


def lock_cleanup_rows(slugs=None):
    targets = cleanup_targets()
    parent_slugs = set(slugs or targets) & targets.keys()
    related_slugs = parent_slugs | {
        slug for parent in parent_slugs for slug in targets[parent]
    }
    if not slugs or 'nova-siluet' in slugs:
        related_slugs.add('nova-siluet')
    # Parent locks serialize new FK references against deletion; child locks
    # prevent their removal while the preserved media rows move to them.
    series = list(
        Series.objects.select_for_update()
        .filter(slug__in=related_slugs)
        .order_by('pk')
    )
    related_ids = [row.pk for row in series]
    parent_ids = [row.pk for row in series if row.slug in parent_slugs]
    for model in (Variant, ConnectionOption, ColorGroup):
        list(
            model.objects.select_for_update()
            .filter(series_id__in=parent_ids)
            .order_by('pk')
        )
    for model in (SeriesImage, SeriesFile, Showcase):
        list(
            model.objects.select_for_update()
            .filter(series_id__in=related_ids)
            .order_by('pk')
        )
    list(
        ProductFamily.objects.select_for_update(of=('self',))
        .filter(presentation_photo__series_id__in=parent_ids)
        .order_by('pk')
    )
    list(
        Project.series.through.objects.select_for_update()
        .filter(series_id__in=parent_ids)
        .order_by('pk')
    )


def apply_cleanup(report):
    media_models = {
        'catalog.seriesimage': SeriesImage,
        'catalog.seriesfile': SeriesFile,
    }
    for parent in report['parents']:
        if parent['status'] != 'eligible':
            continue
        for move in parent['media_moves']:
            media_models[move['model']].objects.filter(pk=move['id']).update(
                series_id=move['series_id'], is_visible=move['is_visible']
            )
        # No dependent media/colors/projects remain. FileField.delete is never
        # called; neither moving a row nor ORM deletion touches storage.
        Series.objects.filter(pk=parent['id']).delete()
    nova = report['nova']
    if nova and nova['status'] == 'eligible':
        Showcase.objects.filter(pk=nova['keep_id']).update(**nova['updates'])
        Showcase.objects.filter(pk__in=nova['remove_ids']).delete()
