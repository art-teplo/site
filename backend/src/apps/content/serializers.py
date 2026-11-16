from urllib.parse import urlparse

from rest_framework import serializers

from .models import (
    FOCUS_CENTER,
    Faq,
    OpeningHours,
    Post,
    Project,
    Promo,
    ShowroomPhoto,
    SiteSettings,
)


def image_asset(obj):
    """Фото в форме ImageAsset фронта.

    Адрес файла — как его отдаёт хранилище: на диске /media/… без домена (сайт и бэк
    на одном домене за nginx, Next берёт фото через свои rewrites), в S3 — полный адрес.
    Домен из запроса не подставляем: Next ходит сюда по http://backend:8000,
    браузеру этот адрес не виден. Так же отдаются видео шоурума и логотипы брендов.
    """
    asset = {
        'src': obj.image.url,
        'width': obj.image_width,
        'height': obj.image_height,
        # Пусто в админке — название записи (default_alt у модели)
        'alt': obj.alt,
    }
    # Точка фокуса «x y» в процентах: фронт ставит её в object-position.
    # Центр не отдаём — это и так поведение по умолчанию
    focus = getattr(obj, 'image_focus', FOCUS_CENTER)
    if focus and focus != FOCUS_CENTER:
        x, y = focus.split()
        asset['focus'] = {'x': int(x), 'y': int(y)}
    return asset


class ImageAssetMixin(serializers.Serializer):
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        return image_asset(obj)


class OpeningHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpeningHours
        fields = ['days', 'time']


class SiteSettingsSerializer(serializers.ModelSerializer):
    hours = OpeningHoursSerializer(many=True)
    phone = serializers.SerializerMethodField()
    phone_href = serializers.SerializerMethodField()
    viber_url = serializers.SerializerMethodField()
    instagram_handle = serializers.SerializerMethodField()
    showroom_video = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = [
            'city',
            'address',
            'map_url',
            'phone',
            'phone_href',
            'email',
            'hours',
            'viber_url',
            'telegram_url',
            'instagram_url',
            'instagram_handle',
            'reply_promise',
            'legal_name',
            'unp',
            'yandex_org_id',
            'showroom_video',
        ]

    def get_phone(self, obj):
        return obj.phone.as_international if obj.phone else ''

    def get_phone_href(self, obj):
        return f'tel:{obj.phone.as_e164}' if obj.phone else ''

    def get_viber_url(self, obj):
        phone = obj.viber_phone or obj.phone
        if not phone:
            return ''
        return f'viber://chat?number=%2B{phone.as_e164.lstrip("+")}'

    def get_instagram_handle(self, obj):
        path = urlparse(obj.instagram_url).path.strip('/')
        return f'@{path}' if path else ''

    def get_showroom_video(self, obj):
        """Видео и постер; без видео — null, на сайте фото «скоро»."""
        if not obj.showroom_video:
            return None
        poster = None
        if obj.showroom_poster:
            poster = {
                'src': obj.showroom_poster.url,
                'width': obj.showroom_poster_width,
                'height': obj.showroom_poster_height,
                'alt': 'Шоурум АртТепло',
            }
        return {
            'src': obj.showroom_video.url,
            'poster': poster,
        }


class FaqSerializer(serializers.ModelSerializer):
    class Meta:
        model = Faq
        fields = ['question', 'answer', 'on_home']


class ProjectSerializer(ImageAssetMixin, serializers.ModelSerializer):
    photos = serializers.SerializerMethodField()
    series_slugs = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'slug',
            'title',
            'place',
            'image',
            'photos',
            'video_url',
            'series_slugs',
        ]

    def get_photos(self, obj):
        return [image_asset(photo) for photo in obj.photos.all()]

    def get_video_url(self, obj):
        return obj.video.url if obj.video else ''

    def get_series_slugs(self, obj):
        # Скрытые серии не отдаём; фильтр в Python — по prefetch, без запроса на проект
        return [s.slug for s in obj.series.all() if s.is_published]


class PostListSerializer(ImageAssetMixin, serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = [
            'slug',
            'title',
            'published_at',
            'read_minutes',
            'image',
            'lead',
        ]


class PostSerializer(PostListSerializer):
    class Meta(PostListSerializer.Meta):
        fields = [
            *PostListSerializer.Meta.fields,
            'body',
        ]


class PromoSerializer(ImageAssetMixin, serializers.ModelSerializer):
    class Meta:
        model = Promo
        fields = [
            'title',
            'image',
            'body',
            'ends_at',
        ]


class ShowroomPhotoSerializer(ImageAssetMixin, serializers.ModelSerializer):
    class Meta:
        model = ShowroomPhoto
        fields = ['image']
