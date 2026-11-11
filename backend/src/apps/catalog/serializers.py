from rest_framework import serializers

from apps.content.serializers import ImageAssetMixin, image_asset

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
