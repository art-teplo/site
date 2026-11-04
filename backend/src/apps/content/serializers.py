from urllib.parse import urlparse

from rest_framework import serializers

from .models import (
    Faq,
    OpeningHours,
    Post,
    Project,
    ShowroomPhoto,
    SiteSettings,
)


def absolute(url, request):
    """Абсолютный адрес: фото грузит Next, видео — браузер со страницы сайта,
    а сайт и бэк могут жить на разных доменах."""
    return request.build_absolute_uri(url) if request else url


def image_asset(obj, request):
    """Фото в форме ImageAsset фронта."""
    return {
        'src': absolute(obj.image.url, request),
        'width': obj.image_width,
        'height': obj.image_height,
        'alt': obj.image_alt,
    }


class ImageAssetMixin(serializers.Serializer):
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        return image_asset(obj, self.context.get('request'))


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

    # Пока настройки не заполнены, телефона нет — отдаём пустые строки
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
        request = self.context.get('request')
        poster = None
        if obj.showroom_poster:
            poster = {
                'src': absolute(obj.showroom_poster.url, request),
                'width': obj.showroom_poster_width,
                'height': obj.showroom_poster_height,
                'alt': 'Шоурум АртТепло',
            }
        return {
            'src': absolute(obj.showroom_video.url, request),
            'poster': poster,
        }


class FaqSerializer(serializers.ModelSerializer):
    class Meta:
        model = Faq
        fields = ['question', 'answer', 'on_home']


class ProjectSerializer(ImageAssetMixin, serializers.ModelSerializer):
    kind = serializers.CharField(source='get_kind_display')
    photos = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'slug',
            'title',
            'kind',
            'place',
            'image',
            'photos',
            'product_slugs',
        ]

    def get_photos(self, obj):
        request = self.context.get('request')
        return [image_asset(photo, request) for photo in obj.photos.all()]


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


class ShowroomPhotoSerializer(ImageAssetMixin, serializers.ModelSerializer):
    class Meta:
        model = ShowroomPhoto
        fields = ['image']
