"""Подтверждённые исполнения: код + подключение Guardo, заводской лист Velar."""

import json
from functools import cache
from pathlib import Path


@cache
def registry():
    return json.loads(
        (
            Path(__file__).resolve().parents[1] / 'data/factory_editions.json'
        ).read_text()
    )


def edition_for_row(row):
    slug = row.series_slug if hasattr(row, 'series_slug') else row.sheet.slug
    # Повторный импорт уже может получить конкретное исполнение.
    for parent, entry in registry()['parents'].items():
        if slug in (parent, *(t['slug'] for t in entry['targets'].values())):
            break
    else:
        return None
    if entry['brand'] == 'velar':
        orientation = row.sheet.orientation
    else:
        parts = row.base_article.split()
        code = parts[1] if len(parts) > 1 else ''
        orientation = registry()['guardo_schemes'].get(
            f'{row.connection}|{code}'
        )
    if orientation not in entry['targets']:
        message = f'Неизвестное исполнение {slug}: {getattr(row, "base_article", "")}, {row.connection}'
        raise ValueError(message)
    return {
        'parent': parent,
        'family_key': entry['family_key'],
        **entry['targets'][orientation],
    }


def legacy_targets():
    return {
        p: tuple(t['slug'] for t in e['targets'].values())
        for p, e in registry()['parents'].items()
    }


def active_split_parents():
    from ..models import Series  # noqa: PLC0415

    slugs = set(Series.objects.values_list('slug', flat=True))
    return {
        p
        for p, e in registry()['parents'].items()
        if any(t['slug'] in slugs for t in e['targets'].values())
    }


def validate_split_parents(active):
    from ..models import Series  # noqa: PLC0415

    pending = (
        Series.objects.filter(slug__in=active, variants__isnull=False)
        .values_list('slug', flat=True)
        .first()
    )
    if pending:
        message = f'Сначала завершите проверенный перенос серии {pending}'
        raise ValueError(message)


def route_grouped(grouped):
    active = active_split_parents()
    validate_split_parents(active.intersection(grouped))
    result = {}
    for slug, bases in grouped.items():
        if slug not in active:
            result[slug] = bases
            continue
        for key, colors in bases.items():
            destinations = {}
            for code, row in colors.items():
                target = edition_for_row(row)
                row.series_slug = target['slug']
                row.series_name = target['name']
                row.orientation = target['orientation']
                destinations.setdefault(target['slug'], {})[code] = row
            if len(destinations) != 1:
                message = f'Положение цвета отличается: {key}'
                raise ValueError(message)
            for destination, values in destinations.items():
                result.setdefault(destination, {})[key] = values
    return result


def route_velar(row, active):
    from dataclasses import replace  # noqa: PLC0415

    if row.sheet.slug in active:
        target = edition_for_row(row)
        row.sheet = replace(
            row.sheet, slug=target['slug'], name=target['name']
        )
    return row
