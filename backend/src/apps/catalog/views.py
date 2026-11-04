from rest_framework import generics

from apps.content.views import PublicReadMixin

from . import serializers
from .models import Brand, Category, LeadTime


class CategoryListView(PublicReadMixin, generics.ListAPIView):
    queryset = Category.objects.filter(is_published=True)
    serializer_class = serializers.CategorySerializer


class BrandListView(PublicReadMixin, generics.ListAPIView):
    queryset = Brand.objects.filter(is_published=True)
    serializer_class = serializers.BrandSerializer


class LeadTimeListView(PublicReadMixin, generics.ListAPIView):
    # Порядок как в админке; скрытый бренд прячет и свои сроки
    queryset = LeadTime.objects.filter(
        brand__is_published=True
    ).select_related(
        'brand',
    )
    serializer_class = serializers.LeadTimeSerializer
