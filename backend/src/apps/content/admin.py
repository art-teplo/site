from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.utils.html import format_html
from solo.admin import SingletonModelAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.forms.widgets import ArrayWidget, WysiwygWidget

from .models import (
    Faq,
    OpeningHours,
    Post,
    Project,
    ProjectPhoto,
    ShowroomPhoto,
    SiteSettings,
)

PREVIEW_HEIGHT = 64


@admin.display(description='фото')
def preview(obj):
    if not obj.image:
        return '—'
    return format_html(
        '<img src="{}" alt="" style="height: {}px; border-radius: 4px">',
        obj.image.url,
        PREVIEW_HEIGHT,
    )


class OpeningHoursInline(TabularInline):
    model = OpeningHours
    extra = 0
    ordering_field = 'position'
    hide_ordering_field = True
    fields = ['days', 'time', 'position']


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonModelAdmin, ModelAdmin):
    inlines = [OpeningHoursInline]
    fieldsets = [
        (
            'Шоурум',
            {'fields': ['city', 'address', 'map_url']},
        ),
        (
            'Связь',
            {
                'fields': [
                    'phone',
                    'email',
                    'viber_phone',
                    'telegram_url',
                    'instagram_url',
                    'reply_promise',
                ],
            },
        ),
        (
            'Реквизиты',
            {'fields': ['legal_name', 'unp']},
        ),
        (
            'Видео шоурума',
            {'fields': ['showroom_video', 'showroom_poster']},
        ),
        (
            'Виджеты',
            {'fields': ['yandex_org_id']},
        ),
    ]


@admin.register(Faq)
class FaqAdmin(ModelAdmin):
    list_display = ['question', 'on_home']
    list_filter = ['on_home']
    search_fields = ['question', 'answer']
    ordering_field = 'position'
    hide_ordering_field = True
    fields = ['question', 'answer', 'on_home']


class ProjectPhotoInline(TabularInline):
    model = ProjectPhoto
    extra = 0
    ordering_field = 'position'
    hide_ordering_field = True
    fields = [preview, 'image', 'image_alt', 'position']
    readonly_fields = [preview]


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    inlines = [ProjectPhotoInline]
    list_display = [preview, 'title', 'kind', 'place', 'is_published']
    list_display_links = ['title']
    list_filter = ['kind', 'is_published']
    search_fields = ['title', 'place']
    ordering_field = 'position'
    hide_ordering_field = True
    prepopulated_fields = {'slug': ['title']}
    formfield_overrides = {
        ArrayField: {'widget': ArrayWidget},
    }
    fields = [
        'title',
        'slug',
        'kind',
        'place',
        'image',
        'image_alt',
        'product_slugs',
        'is_published',
    ]


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = [preview, 'title', 'published_at', 'is_published']
    list_display_links = ['title']
    list_filter = ['is_published']
    search_fields = ['title', 'lead']
    date_hierarchy = 'published_at'
    prepopulated_fields = {'slug': ['title']}
    fields = [
        'title',
        'slug',
        'published_at',
        'image',
        'image_alt',
        'lead',
        'body',
        'is_published',
    ]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # Редактор — только для текста статьи, лид — обычное поле
        if db_field.name == 'body':
            kwargs['widget'] = WysiwygWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(ShowroomPhoto)
class ShowroomPhotoAdmin(ModelAdmin):
    list_display = [preview, 'image_alt']
    list_display_links = ['image_alt']
    ordering_field = 'position'
    hide_ordering_field = True
    fields = ['image', 'image_alt']
