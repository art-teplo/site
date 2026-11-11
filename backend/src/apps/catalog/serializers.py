from rest_framework import serializers

from apps.content.serializers import ImageAssetMixin, image_asset

from . import schema
from .models import Brand, Category, LeadTime


class CategorySerializer(ImageAssetMixin, serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['slug', 'name', 'short', 'image']


class BrandSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = ['slug', 'name', 'country', 'note', 'logo', 'warranty_years']

    def get_logo(self, obj):
        return obj.logo.url if obj.logo else None


class LeadTimeSerializer(serializers.ModelSerializer):
    brand = serializers.SlugRelatedField(slug_field='slug', read_only=True)

    class Meta:
        model = LeadTime
        fields = ['series', 'brand', 'days', 'updated_at']


def card_image(showcase, series):
    """Фото витрины, иначе первое фото серии, иначе None."""
    if showcase is not None and showcase.image:
        return image_asset(showcase)
    return series_image(series)


def series_image(series):
    images = list(series.images.all())
    return image_asset(images[0]) if images else None


def card(series, showcase, price, colors):
    """Карточка списка: серия в одном формфакторе."""
    variant = showcase.variant if showcase is not None else None
    return {
        'series': series.slug,
        'name': series.name,
        'brand': series.brand.slug,
        'label': showcase.label if showcase is not None else '',
        'height_mm': variant.height_mm if variant is not None else None,
        'price_from': price,
        'image': card_image(showcase, series),
        'colors': colors,
    }


def tile(series):
    """Плитка модельного ряда бренда."""
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
        'percent': float(group.percent),
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
        'orientation': image.orientation,
    }


def series_detail(
    series,
    *,
    ranges: dict,
    executions: list[dict],
    columns: list[schema.Field],
    filters: list[schema.Field],
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
        'material': series.material,
        'heating': series.heating,
        'pressure_bar': series.pressure_bar,
        'warranty_years': series.warranty,
        'video_url': series.video_url,
        'images': [series_image_full(i) for i in series.images.all()],
        'files': [
            {'title': f.title, 'url': f.file.url} for f in series.files.all()
        ],
        'color_groups': [color_group(g) for g in series.color_groups.all()],
        'ranges': ranges,
        'executions': executions,
        'default_execution': executions[0]['key'] if executions else None,
        'columns': [field(f) for f in columns],
        'filters': [field(f) for f in filters],
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
    }
