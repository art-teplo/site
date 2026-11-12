from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import redirect
from django.utils.html import format_html
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action

from apps.content.admin import PREVIEW_HEIGHT, preview
from apps.content.models import Tag
from apps.content.tasks import revalidate_frontend

from . import pricing
from .models import (
    Brand,
    Category,
    Color,
    ColorGroup,
    CurrencyRate,
    LeadTime,
    Series,
    SeriesFile,
    SeriesImage,
    Showcase,
    Subcategory,
    Variant,
)
from .tasks import update_rates


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


@admin.register(Subcategory)
class SubcategoryAdmin(ModelAdmin):
    list_display = [preview, 'name', 'category', 'is_published']
    list_display_links = ['name']
    list_filter = ['category', 'is_published']
    search_fields = ['name']
    ordering_field = 'position'
    hide_ordering_field = True
    prepopulated_fields = {'slug': ['name']}
    fields = [
        'category',
        'name',
        'slug',
        'image',
        'image_alt',
        'is_published',
    ]


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
        'markup_percent',
        'is_published',
    ]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and 'markup_percent' in form.changed_data:
            # bulk_update сигналов не шлёт; кэш сбросит сохранение бренда
            pricing.recalculate(Variant.objects.filter(brand=obj))


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


@admin.display(description='цвет')
def color_swatch(obj):
    return format_html(
        '<span style="display: inline-block; width: 20px; height: 20px; '
        'border-radius: 50%; border: 1px solid #8884; '
        'background: {}"></span>',
        obj.hex,
    )


@admin.register(Color)
class ColorAdmin(ModelAdmin):
    list_display = [color_swatch, 'code', 'name', 'finish']
    list_display_links = ['code']
    list_filter = ['finish']
    search_fields = ['code', 'name']
    fields = ['code', 'name', 'hex', 'finish']


class ColorGroupInline(TabularInline):
    model = ColorGroup
    extra = 0
    ordering_field = 'position'
    hide_ordering_field = True
    fields = ['name', 'percent', 'is_base', 'any_ral', 'colors']
    autocomplete_fields = ['colors']


class SeriesImageInline(TabularInline):
    model = SeriesImage
    extra = 0
    ordering_field = 'position'
    hide_ordering_field = True
    fields = [
        preview,
        'image',
        'image_alt',
        'kind',
        'color',
        'orientation',
    ]
    readonly_fields = [preview]
    autocomplete_fields = ['color']


class SeriesFileInline(TabularInline):
    model = SeriesFile
    extra = 0
    ordering_field = 'position'
    hide_ordering_field = True
    fields = ['title', 'file']


class ShowcaseInline(StackedInline):
    model = Showcase
    extra = 0
    ordering_field = 'position'
    hide_ordering_field = True
    fields = ['label', 'variant', 'image', 'image_alt']
    autocomplete_fields = ['variant']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'variant':
            series_id = (request.resolver_match.kwargs or {}).get('object_id')
            # автодополнение ищет по всем вариантам и queryset не учитывает;
            # он нужен для проверки при сохранении: чужой вариант не пройдёт
            field.queryset = Variant.objects.filter(series_id=series_id)
        return field


@admin.register(Series)
class SeriesAdmin(ModelAdmin):
    inlines = [
        ColorGroupInline,
        SeriesImageInline,
        SeriesFileInline,
        ShowcaseInline,
    ]
    list_display = [
        'name',
        'brand',
        'category',
        'subcategory',
        'heating',
        'is_published',
    ]
    list_display_links = ['name']
    list_filter = [
        'brand',
        'category',
        'subcategory',
        'heating',
        'is_published',
    ]
    search_fields = ['name']
    ordering_field = 'position'
    hide_ordering_field = True
    fields = [
        'brand',
        'category',
        'subcategory',
        'name',
        'description',
        'material',
        'heating',
        'pressure_bar',
        'warranty_years',
        'video_url',
        'is_published',
    ]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and 'brand' in form.changed_data:
            # Variant.brand копируется из серии только в save(); кэш сбросит
            # сигнал сохранения серии
            obj.variants.update(brand=obj.brand)
            pricing.recalculate(obj.variants.all())

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'description':
            kwargs['widget'] = WysiwygWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class VariantForm(forms.ModelForm):
    class Meta:
        model = Variant
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        series_id = self.instance.series_id
        # новый вариант: серия ещё не выбрана — группы не предлагаем
        self.fields['color_groups'].queryset = ColorGroup.objects.filter(
            series_id=series_id,
        )

    def clean(self):
        cleaned = super().clean()
        series = cleaned.get('series')
        groups = cleaned.get('color_groups')
        if series and groups and groups.exclude(series=series).exists():
            self.add_error(
                'color_groups',
                'Группы цветов должны быть из серии варианта',
            )
        return cleaned


@admin.register(Variant)
class VariantAdmin(ModelAdmin):
    form = VariantForm
    list_display = [
        'article',
        'series',
        'height_mm',
        'width_mm',
        'power_w',
        'connection',
        'price',
        'currency',
        'price_byn',
        'is_active',
    ]
    list_display_links = ['article']
    list_filter = ['series__brand', 'series', 'connection', 'is_active']
    list_select_related = ['series']
    search_fields = ['article']
    autocomplete_fields = ['series']
    readonly_fields = ['price_byn']
    fieldsets = [
        (None, {'fields': ['series', 'article', 'is_active']}),
        (
            'Размеры и мощность',
            {
                'fields': [
                    'height_mm',
                    'width_mm',
                    'depth_mm',
                    'length_mm',
                    'axis_mm',
                    'sections',
                    'power_w',
                    'tubes',
                ],
            },
        ),
        (
            'Подключение и монтаж',
            {'fields': ['connection', 'thermovalve', 'orientation', 'mount']},
        ),
        ('Цена', {'fields': ['price', 'currency', 'price_byn']}),
        ('Прочее', {'fields': ['attrs', 'color_groups']}),
    ]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        pricing.recalculate(Variant.objects.filter(pk=obj.pk))
        obj.refresh_from_db(fields=['price_byn'])
        self.revalidate()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        self.revalidate()

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        self.revalidate()

    @staticmethod
    def revalidate():
        # у Variant нет cache_tag (массовые правки) — сбрасываем кэш сами
        transaction.on_commit(lambda: revalidate_frontend.delay(Tag.CATALOG))


@admin.register(CurrencyRate)
class CurrencyRateAdmin(ModelAdmin):
    """Курсы тянет задача по расписанию, руками их не правят."""

    list_display = ['currency', 'rate', 'date']
    list_filter = ['currency']
    date_hierarchy = 'date'
    actions_list = ['update_now']

    @action(
        description='Обновить курсы сейчас',
        permissions=['view'],
    )
    def update_now(self, request):
        # Только тянет публичные курсы Нацбанка — менеджеру можно
        update_rates.delay()
        self.message_user(
            request,
            'Курсы запрошены, цены пересчитаются в течение минуты',
            messages.SUCCESS,
        )
        return redirect('admin:catalog_currencyrate_changelist')

    def has_add_permission(self, request):  # noqa: ARG002
        return False

    def has_change_permission(self, request, obj=None):  # noqa: ARG002
        return False

    def has_delete_permission(self, request, obj=None):  # noqa: ARG002
        return False
