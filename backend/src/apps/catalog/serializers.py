from rest_framework import serializers

from apps.content.serializers import ImageAssetMixin, image_asset

from . import schema
from .models import Brand, Category, LeadTime, SeriesImage
from .pricing import effective_percent


class CategorySerializer(ImageAssetMixin, serializers.ModelSerializer):
    series_count = serializers.IntegerField(read_only=True)
    types = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['slug', 'name', 'short', 'image', 'series_count', 'types']

    def get_types(self, obj):
        # Опубликованные типы с series_count — prefetch в CategoryListView
        return [
            {
                'slug': t.slug,
                'name': t.name,
                'image': image_asset(t) if t.image else None,
                'series_count': t.series_count,
            }
            for t in obj.types.all()
        ]


class BrandSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    series_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Brand
        fields = [
            'slug',
            'name',
            'country',
            'note',
            'logo',
            'warranty_years',
            'series_count',
        ]

    def get_logo(self, obj):
        return obj.logo.url if obj.logo else None


class LeadTimeSerializer(serializers.ModelSerializer):
    brand = serializers.SlugRelatedField(slug_field='slug', read_only=True)

    class Meta:
        model = LeadTime
        fields = ['series', 'brand', 'days', 'updated_at']


def _photos(series) -> list:
    """Фото серии без схем: схема подключений — не фото товара."""
    return [
        i
        for i in series.images.all()
        if i.is_visible and i.kind != SeriesImage.Kind.SCHEME
    ]


def _card_photo(showcase, series):
    """Своя обложка витрины или первое товарное фото серии."""
    if showcase is not None and showcase.image:
        return showcase
    return _main_image(series)


def card_image(showcase, series):
    """Фото витрины или подходящее фото серии."""
    image = _card_photo(showcase, series)
    return image_asset(image) if image is not None else None


def _main_image(series):
    """Главное фото серии: первое «товарное», иначе первое любое."""
    images = _photos(series)
    product = [i for i in images if i.kind == SeriesImage.Kind.PRODUCT]
    return (product or images or [None])[0]


def series_image(series):
    image = _main_image(series)
    return image_asset(image) if image is not None else None


def hover_image(series, showcase=None):
    """Фото при наведении: первое «в интерьере», иначе второе «товарное»;
    отличается от фото на карточке."""
    shown = _card_photo(showcase, series)
    images = [
        i for i in _photos(series) if not shown or i.image != shown.image
    ]
    interior = [i for i in images if i.kind == SeriesImage.Kind.INTERIOR]
    product = [i for i in images if i.kind == SeriesImage.Kind.PRODUCT]
    if interior:
        return image_asset(interior[0])
    return image_asset(product[0]) if product else None


def card(series, showcase, price, colors, label=''):
    """Карточка серии с автоматической подписью по размерам."""
    return {
        'series': series.slug,
        'name': series.name,
        'brand': series.brand.slug,
        'category': series.category.slug,
        'label': label,
        'price_from': price,
        'image': card_image(showcase, series),
        'hover_image': hover_image(series, showcase),
        'type': series.subcategory.slug if series.subcategory else None,
        'colors': colors,
    }


def tile(series):
    """Плитка модельного ряда бренда."""
    family = series.family if series.family_id else None
    if family and family.presentation_photo_id:
        return {
            'series': f'{series.brand.slug}-{family.key}',
            'name': f'{series.brand.name} {family.name}',
            'image': image_asset(family.presentation_photo),
        }
    return {
        'series': series.slug,
        'name': series.name,
        'image': series_image(series),
    }


def field(item: schema.Field) -> dict:
    return {
        'key': item.key,
        'label': item.label,
        'kind': item.kind,
        'unit': item.unit,
    }


def color_group(group) -> dict:
    return {
        'id': group.pk,
        'name': group.name,
        'percent': effective_percent(group),
        'is_base': group.is_base,
        'any_ral': group.any_ral,
        'colors': [
            {
                'code': color.code,
                'name': color.name,
                'hex': color.hex,
                'finish': color.finish,
            }
            for color in group.colors.all()
        ],
    }


def series_image_full(image) -> dict:
    return {
        **image_asset(image),
        'color': image.color.code if image.color else None,
        'kind': image.kind,
    }


def series_detail(
    series,
    *,
    ranges: dict,
    range_steps: dict,
    price_from: int | None,
    price_from_by_group: dict[int, int | None],
    executions: list[dict],
    columns: list[schema.Field],
    filters: list[schema.Field],
    similar: list[dict],
    projects: list[dict],
) -> dict:
    return {
        'slug': series.slug,
        'name': series.name,
        'category': series.category.slug,
        'brand': {
            'slug': series.brand.slug,
            'name': series.brand.name,
            'country': series.brand.country,
        },
        'description': series.description,
        'factory_orientation': series.factory_orientation or None,
        'editions': [
            {
                'slug': s.slug,
                'orientation': s.factory_orientation or None,
                'label': s.family_label
                or s.get_factory_orientation_display()
                or s.name,
            }
            for s in series.family.series.filter(
                is_published=True, variants__is_active=True
            )
            .order_by('factory_orientation', 'family_label', 'pk')
            .distinct()
        ]
        if series.family_id
        else [],
        'material': series.material,
        'heating': series.heating,
        'pressure_bar': series.pressure_bar,
        'warranty_years': series.warranty,
        # Файл в S3; ключ прежний — фронт ждёт адрес, пусто — видео нет
        'video_url': series.video.url if series.video else '',
        'images': [
            series_image_full(i) for i in series.images.all() if i.is_visible
        ],
        'files': [
            {'title': f.title, 'url': f.file.url}
            for f in series.files.all()
            if f.is_visible
        ],
        'color_groups': [color_group(g) for g in series.color_groups.all()],
        'ranges': ranges,
        'range_steps': range_steps,
        'price_from': price_from,
        'price_from_by_group': price_from_by_group,
        'executions': executions,
        'default_execution': executions[0]['key'] if executions else None,
        'columns': [field(f) for f in columns],
        'filters': [field(f) for f in filters],
        'similar': similar,
        'projects': projects,
    }


def row(variant, price: int | None) -> dict:
    return {
        'article': variant.article,
        'height_mm': variant.height_mm,
        'width_mm': variant.width_mm,
        'depth_mm': variant.depth_mm,
        'length_mm': variant.length_mm,
        'axis_mm': variant.axis_mm,
        'sections': variant.sections,
        'power_w': variant.power_w,
        'area_m2': (
            round(variant.power_w / schema.WATTS_PER_M2, 1)
            if variant.power_w is not None
            else None
        ),
        'tubes': variant.tubes,
        'connection': variant.connection,
        'thermovalve': variant.thermovalve,
        'orientation': variant.orientation,
        'mount': variant.mount,
        'attrs': variant.attrs,
        'price': price,
        # Цена без цвета и группы варианта: фронт пересчитывает цену при
        # смене цвета сразу, не дожидаясь ответа (lib/price.ts rowPrice)
        'price_byn': (
            float(variant.price_byn) if variant.price_byn is not None else None
        ),
        'color_groups': [g.pk for g in variant.color_groups.all()],
    }
