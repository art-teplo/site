"""Прямые варианты из розничных прайсов Радимакс в BYN."""

import csv
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from django.db import transaction

from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend

from ..choices import Mount
from ..finishes import ensure_any_ral
from ..models import (
    Brand,
    Category,
    Color,
    ColorGroup,
    Series,
    Subcategory,
    Variant,
)
from ..pricing import recalculate
from .product_families import assign_family

PRICE_SOURCE = Path(__file__).resolve().parents[1] / 'data/radimax_price.csv'
NAMES = {
    'still-azhur': 'Стилл Ажур',
    'still-vintazh': 'Стилл Винтаж',
}
SPLIT_SERIES = {
    'heat',
    'loft',
    'derby',
    'windsbold',
    'bristol',
    'windsor',
    'york',
    'soul',
}
STILL_COLORS = (
    ('Белый', 'Белый', '#ffffff', ''),
    ('RAL 7024', 'Графитовый', '#474a50', 'matte'),
    ('RAL 9005', 'Чёрный', '#0e0e10', 'matte'),
    ('RAL 1013', 'Бежевый', '#ded3b6', 'matte'),
)
# Производитель подписал эти фотографии названиями отделок. Цвет в
# справочнике приблизительный, группа цен из этих образцов не создаётся.
PHOTO_FINISHES = {
    'Old Silver Standart': '#585848',
    'Какао + белый': '#b8a898',
}


def ensure_photo_finishes():
    for code, hex_value in PHOTO_FINISHES.items():
        Color.objects.get_or_create(
            code=code, defaults={'name': code, 'hex': hex_value}
        )


def read_price(path=PRICE_SOURCE):
    with path.open(encoding='utf-8', newline='') as source:
        return list(csv.DictReader(source))


def model_slug(series, model):
    key = model.lower().replace(' ', '-').replace('/', '-')
    return f'radimax-{key if series in SPLIT_SERIES else series}'


def _visible_sections(series, count):
    if series == 'lynn':
        return 2 <= count <= 15
    return series.startswith('still-') or count >= 3


def build_variants(rows):
    for row in rows:
        series = row['series']
        if '-' in row['sections']:
            minimum, maximum = map(int, row['sections'].split('-'))
            counts = range(minimum, maximum + 1)
        else:
            counts = list(map(int, row['sections'].split('/')))

        heights = row['wall_height_mm'], row['floor_height_mm']
        depths = row['wall_depth_mm'], row['floor_depth_mm']
        if heights[1]:
            mounts = [
                (Mount.WALL, heights[0], depths[0]),
                (Mount.FLOOR, heights[1], depths[1] or depths[0]),
            ]
        else:
            mounts = [('', heights[0], depths[0])]

        model = row['model'].replace(' ', '-').replace('/', '-')
        section_price = Decimal(row['price_byn'])
        for mount, height, depth in mounts:
            for count in counts:
                width = Decimal(row['section_width_mm']) * count
                attrs = {
                    'factory_model': row['model'],
                    'section_width_mm': row['section_width_mm'],
                }
                for key in (
                    'section_mass_kg',
                    'section_volume_l',
                    'pressure_atm',
                ):
                    if row[key]:
                        attrs[key] = row[key]
                if depths[1] and not heights[1]:
                    attrs['source_depth_mm'] = '/'.join(depths)
                if width != int(width):
                    attrs['source_width_mm'] = str(width)

                article = '-'.join(
                    filter(None, (model, mount.upper(), str(count)))
                )
                yield {
                    'series': model_slug(series, row['model']),
                    'former_series': f'radimax-{series}',
                    'article': article,
                    'height_mm': int(height),
                    'depth_mm': int(depth),
                    'width_mm': int(
                        width.to_integral_value(rounding=ROUND_HALF_UP)
                    ),
                    'axis_mm': int(row['axis_mm']),
                    'sections': count,
                    'is_active': _visible_sections(series, count),
                    'power_w': int(row['section_power_w']) * count,
                    'mount': mount,
                    'price': section_price * count,
                    'currency': 'BYN',
                    'attrs': attrs,
                }


def _add_still_colors(series):
    if series.color_groups.exists():
        return
    group = ColorGroup.objects.create(
        series=series, name='Базовые цвета Стилл', is_base=True
    )
    for code, name, hex_value, finish in STILL_COLORS:
        color, _ = Color.objects.get_or_create(
            code=code,
            defaults={'name': name, 'hex': hex_value, 'finish': finish},
        )
        group.colors.add(color)


def _series_for_model(slug, values, brand, category, subcategories):
    key = slug.removeprefix('radimax-')
    still = key.startswith('still-')
    subcategory = subcategories.get('stalnye' if still else 'chugunnye')
    model = values['attrs']['factory_model']
    name = NAMES.get(key, model.title().replace('Soul ', 'Соул '))
    series, _ = Series.objects.get_or_create(
        slug=slug,
        brand=brand,
        defaults={
            'name': f'Радимакс {name}',
            'category': category,
            'subcategory': subcategory,
            'material': 'Сталь' if still else 'Чугун',
            'warranty_years': 10 if still else 5,
            'is_published': False,
            'description': 'Окраска в любой RAL по запросу.',
        },
    )
    if still:
        _add_still_colors(series)
    changed_type = (
        subcategory is not None and series.subcategory_id != subcategory.pk
    )
    if changed_type:
        series.subcategory = subcategory
        series.save(update_fields=['subcategory'])
    if key == 'lynn' and series.name == 'Радимакс Lynn':
        series.name = f'Радимакс {name}'
        series.save(update_fields=['name'])
    return series, changed_type


def import_radimax(variants):
    counts = {
        'created': 0,
        'updated': 0,
        'unchanged': 0,
        'reclassified': 0,
        'family_linked': 0,
        'ral_added': 0,
    }
    with muted_revalidation(), transaction.atomic():
        brand, _ = Brand.objects.get_or_create(
            slug='radimax',
            defaults={
                'name': 'Радимакс',
                'country': 'Россия',
                'is_published': False,
            },
        )
        ensure_photo_finishes()
        category, _ = Category.objects.get_or_create(
            slug='radiatory',
            defaults={'name': 'Радиаторы', 'is_published': False},
        )
        subcategories = {
            item.slug: item
            for item in Subcategory.objects.filter(
                category=category, slug__in=('chugunnye', 'stalnye')
            )
        }
        by_slug = {}
        for values in variants:
            slug = values['series']
            series = by_slug.get(slug)
            if series is None:
                series, reclassified = _series_for_model(
                    slug, values, brand, category, subcategories
                )
                counts['family_linked'] += assign_family(series)
                counts['reclassified'] += reclassified
                counts['ral_added'] += ensure_any_ral(series)
                by_slug[slug] = series

            attrs = {
                key: value
                for key, value in values.items()
                if key
                not in ('series', 'former_series', 'article', 'is_active')
            }
            variant, created = Variant.objects.get_or_create(
                brand=brand,
                article=values['article'],
                connection='',
                defaults={
                    'series': series,
                    'is_active': values['is_active'],
                    **attrs,
                },
            )
            if created:
                counts['created'] += 1
                continue
            if variant.series_id != series.pk:
                if variant.series.slug != values['former_series']:
                    msg = f'Артикул {variant.article} уже привязан к другой серии'
                    raise ValueError(msg)
                attrs['series_id'] = series.pk
            attrs['attrs'] = variant.attrs | attrs['attrs']
            # Импорт может скрыть размер вне диапазона, но сохраняет ручное отключение.
            if not values['is_active']:
                attrs['is_active'] = False
            changed = [
                key
                for key, value in attrs.items()
                if getattr(variant, key) != value
            ]
            if changed:
                for key in changed:
                    setattr(variant, key, attrs[key])
                variant.save(update_fields=changed)
                counts['updated'] += 1
            else:
                counts['unchanged'] += 1

        recalculate(Variant.objects.filter(series__in=by_slug.values()))
        if any(value for key, value in counts.items() if key != 'unchanged'):
            transaction.on_commit(
                lambda: revalidate_frontend.delay(Tag.CATALOG)
            )
    return counts
