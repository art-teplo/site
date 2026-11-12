from rest_framework import generics, permissions

from . import serializers
from .models import Faq, Post, Project, Promo, ShowroomPhoto, SiteSettings


class PublicReadMixin:
    """Открытое чтение без сессии; списки короткие — без пагинации.
    Страницы кэширует фронт, сюда он ходит только после правки."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class SiteView(PublicReadMixin, generics.RetrieveAPIView):
    serializer_class = serializers.SiteSettingsSerializer

    def get_object(self):
        return SiteSettings.get_solo()


class FaqListView(PublicReadMixin, generics.ListAPIView):
    queryset = Faq.objects.all()
    serializer_class = serializers.FaqSerializer


class ProjectListView(PublicReadMixin, generics.ListAPIView):
    queryset = Project.objects.filter(is_published=True).prefetch_related(
        'photos',
        'series',
    )
    serializer_class = serializers.ProjectSerializer


class PostListView(PublicReadMixin, generics.ListAPIView):
    queryset = Post.objects.filter(is_published=True)
    serializer_class = serializers.PostListSerializer


class PostDetailView(PublicReadMixin, generics.RetrieveAPIView):
    queryset = Post.objects.filter(is_published=True)
    serializer_class = serializers.PostSerializer
    lookup_field = 'slug'


class PromoListView(PublicReadMixin, generics.ListAPIView):
    serializer_class = serializers.PromoSerializer

    def get_queryset(self):
        return Promo.objects.active()


class ShowroomView(PublicReadMixin, generics.ListAPIView):
    queryset = ShowroomPhoto.objects.all()
    serializer_class = serializers.ShowroomPhotoSerializer
