"""Заводские исполнения и прежние объединённые адреса КЗТО."""

from dataclasses import replace

LEGACY_SERIES = {
    'kzto-quadrum-30': ('kzto-quadrum-30-v', 'kzto-quadrum-30-h'),
    'kzto-quadrum-40': ('kzto-quadrum-40-v', 'kzto-quadrum-40-h'),
    'kzto-quadrum-50': ('kzto-quadrum-50-v', 'kzto-quadrum-50-h'),
    'kzto-quadrum-60': ('kzto-quadrum-60-v', 'kzto-quadrum-60-h'),
    'kzto-quadrum-neo-50': ('kzto-quadrum-neo-50-v', 'kzto-quadrum-neo-50-h'),
    'kzto-ellipse-p': ('kzto-ellipse-p-v', 'kzto-ellipse-p-h'),
    'kzto-ellipse-s': ('kzto-ellipse-s-v', 'kzto-ellipse-s-h'),
    'kzto-solo': ('kzto-solo-v', 'kzto-solo-g'),
    'kzto-paralleli': ('kzto-paralleli-v', 'kzto-paralleli-g'),
}


def separate_targets(targets):
    result = {}
    for category, target in targets.items():
        if target.slug in LEGACY_SERIES:
            slug = LEGACY_SERIES[target.slug][
                0 if target.orientation == 'v' else 1
            ]
            suffix = category.rsplit(' ', 1)[-1]
            target = replace(target, slug=slug, name=f'{target.name} {suffix}')
        result[category] = target
    return result
