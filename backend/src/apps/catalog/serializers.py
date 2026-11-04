from rest_framework import serializers

from apps.content.serializers import ImageAssetMixin, absolute

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
        if not obj.logo:
            return None
        return {
            'src': absolute(obj.logo.url, self.context.get('request')),
            'width': obj.logo_width,
            'height': obj.logo_height,
        }


class LeadTimeSerializer(serializers.ModelSerializer):
    brand = serializers.SlugRelatedField(slug_field='slug', read_only=True)

    class Meta:
        model = LeadTime
        fields = ['series', 'brand', 'days', 'updated_at']
