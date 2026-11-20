"""Явная заводская принадлежность; геометрия не определяет положение."""

import json
from functools import cache
from pathlib import Path

from ..models import ProductFamily


def import_traits(series, values, variant=None):
    values = dict(values)
    confirmed = (
        (variant.attrs or {}).get('confirmed_fields', []) if variant else []
    )
    for name in ('orientation', 'mount', 'thermovalve'):
        if name in confirmed and name in values:
            known, incoming = getattr(variant, name), values[name]
            if incoming not in ('', None) and known != incoming:
                message = f'Подтверждённый {name} противоречит источнику: {variant.article}'
                raise ValueError(message)
            values[name] = known
    orientation = values.get('orientation')
    if (
        series.factory_orientation
        and orientation
        and series.factory_orientation != orientation
    ):
        message = f'Положение противоречит серии {series.slug}'
        raise ValueError(message)
    return values


@cache
def family_registry():
    return json.loads(
        (
            Path(__file__).resolve().parents[1] / 'data/product_families.json'
        ).read_text()
    )


def family_for_target(brand_slug: str, series_slug: str) -> dict | None:
    entry = family_registry().get(series_slug)
    return entry if entry and entry['brand'] == brand_slug else None


def radimax_legacy_targets():
    targets = {}
    for slug, entry in family_registry().items():
        if entry['brand'] == 'radimax':
            parent = f'radimax-{entry["key"]}'
            if parent != slug:
                targets.setdefault(parent, []).append(slug)
    return targets


def assign_family(series):
    entry = family_for_target(series.brand.slug, series.slug)
    if entry is None or series.category.slug != 'radiatory':
        return False
    orientation = entry['orientation']
    if (
        orientation
        and series.factory_orientation
        and orientation != series.factory_orientation
    ):
        message = f'Положение {series.slug}: источник противоречит подтверждённому значению'
        raise ValueError(message)
    if series.family_id:
        fields = []
        if orientation and not series.factory_orientation:
            series.factory_orientation = orientation
            fields.append('factory_orientation')
        if entry.get('label') and not series.family_label:
            series.family_label = entry['label']
            fields.append('family_label')
        if fields:
            series.full_clean()
            series.save(update_fields=fields)
            return True
        return False
    family, _ = ProductFamily.objects.get_or_create(
        brand=series.brand,
        key=entry['key'],
        defaults={'category': series.category, 'name': entry['name']},
    )
    if family.category_id != series.category_id:
        message = 'Категория линейки не совпадает с серией'
        raise ValueError(message)
    changed = (
        series.family_id != family.pk
        or series.factory_orientation != entry['orientation']
    )
    if changed:
        series.family = family
        series.factory_orientation = orientation or series.factory_orientation
        series.family_label = series.family_label or entry.get('label', '')
        series.full_clean()
        series.save(
            update_fields=['family', 'factory_orientation', 'family_label']
        )
    return changed
