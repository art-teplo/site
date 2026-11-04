from django import forms
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from apps.content.admin import PREVIEW_HEIGHT, preview

from .models import Brand, Category, LeadTime


@admin.display(description='логотип')
def logo_preview(obj):
    if not obj.logo:
        return '—'
    return format_html(
        '<img src="{}" alt="" style="height: {}px; max-width: 160px">',
        obj.logo.url,
        PREVIEW_HEIGHT // 2,
    )


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = '__all__'
        help_texts = {
            'slug': (
                'Латиницей, в адресе страницы. Товары ссылаются на него — '
                'у существующей категории не меняйте'
            ),
            'image': 'Товар без фона: PNG или WebP с прозрачностью, от 800 px',
        }


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    form = CategoryForm
    list_display = [preview, 'name', 'short', 'is_published']
    list_display_links = ['name']
    ordering_field = 'position'
    hide_ordering_field = True
    prepopulated_fields = {'slug': ['name']}
    fields = ['name', 'slug', 'short', 'image', 'image_alt', 'is_published']


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = [
        logo_preview,
        'name',
        'country',
        'warranty_years',
        'is_published',
    ]
    list_display_links = ['name']
    list_filter = ['is_published']
    search_fields = ['name']
    ordering_field = 'position'
    hide_ordering_field = True
    prepopulated_fields = {'slug': ['name']}
    fields = [
        'name',
        'slug',
        'country',
        'note',
        'logo',
        'warranty_years',
        'is_published',
    ]


@admin.register(LeadTime)
class LeadTimeAdmin(ModelAdmin):
    """Вся таблица сроков одним списком — порядок как на сайте."""

    list_display = ['series', 'brand', 'days']
    list_editable = ['days']
    list_filter = ['brand']
    search_fields = ['series']
    ordering_field = 'position'
    hide_ordering_field = True
    autocomplete_fields = ['brand']
    fields = ['brand', 'series', 'days']
