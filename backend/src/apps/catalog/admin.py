from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action

from apps.content.admin import PREVIEW_HEIGHT, SortableInlineMixin, preview
from apps.content.models import Tag
from apps.content.tasks import revalidate_frontend
from apps.content.widgets import (
    ImageAdminMixin,
    ImageModelForm,
    InlineImagesAdminMixin,
)

from . import pricing
from .admin_forms import ConnectionOptionForm, ConnectionPreviewForm
from .models import (
    Brand,
    Category,
    Color,
    ColorGroup,
    ConnectionOption,
    CurrencyRate,
    LeadTime,
    ProductFamily,
    Series,
    SeriesFile,
    SeriesImage,
    Showcase,
    Subcategory,
    Variant,
)
from .offers import offer_query
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
class SubcategoryAdmin(ImageAdminMixin, ModelAdmin):
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
        'image_focus',
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


class ColorGroupInline(SortableInlineMixin, TabularInline):
    model = ColorGroup
    extra = 0
    fields = ['name', 'percent', 'is_base', 'any_ral', 'colors', 'position']
    autocomplete_fields = ['colors']


class SeriesImageInline(SortableInlineMixin, TabularInline):
    model = SeriesImage
    form = ImageModelForm
    extra = 0
    fields = [
        preview,
        'image',
        'image_alt',
        'image_focus',
        'kind',
        'is_visible',
        'color',
        'position',
    ]
    readonly_fields = [preview]
    autocomplete_fields = ['color']


class SeriesFileInline(SortableInlineMixin, TabularInline):
    model = SeriesFile
    extra = 0
    fields = ['title', 'file', 'is_visible', 'position']


@admin.register(ConnectionOption)
class ConnectionOptionAdmin(ModelAdmin):
    form = ConnectionOptionForm
    list_display = [
        'series',
        'tubes',
        'label',
        'mount',
        'total_surcharge',
        'checked_on',
    ]
    list_filter = ['series', 'tubes', 'mount', 'thermovalve']
    search_fields = ['series__name', 'label', 'source_id']
    autocomplete_fields = ['series']
    readonly_fields = [
        'source_id',
        'source_url',
        'checked_on',
        'evidence',
        'surcharge_rub',
        'base_adjustment_rub',
        'preview_link',
    ]
    fieldsets = [
        (
            None,
            {
                'fields': [
                    'series',
                    'label',
                    'tubes',
                    'connection',
                    'mount',
                    'thermovalve',
                    'allowed_sections',
                    'configuration_surcharge_rub',
                    'preview_link',
                ]
            },
        ),
        (
            'Источник данных',
            {
                'classes': ['collapse'],
                'fields': [
                    'surcharge_rub',
                    'base_adjustment_rub',
                    'source_id',
                    'source_url',
                    'checked_on',
                    'evidence',
                ],
            },
        ),
    ]

    def has_add_permission(self, request):  # noqa: ARG002
        return False

    def has_delete_permission(self, request, obj=None):  # noqa: ARG002
        return False  # заводские ключи нужны существующим ссылкам; правим, не удаляем

    @admin.display(description='Доплата за конфигурацию, RUB')
    def total_surcharge(self, obj):
        return (
            None
            if obj.surcharge_rub is None
            else obj.surcharge_rub + obj.base_adjustment_rub
        )

    @admin.display(description='Предварительный расчёт')
    def preview_link(self, obj):
        if not obj or not obj.pk:
            return '—'
        return format_html(
            '<a href="{}">Выбрать базовый артикул и посмотреть цену</a>',
            reverse('admin:catalog_connectionoption_preview', args=[obj.pk]),
        )

    def get_urls(self):
        return [
            path(
                '<int:object_id>/preview/',
                self.admin_site.admin_view(self.preview_view),
                name='catalog_connectionoption_preview',
            ),
            *super().get_urls(),
        ]

    def preview_view(self, request, object_id):
        obj = self.get_object(request, str(object_id))
        if obj is None:
            raise Http404
        if not self.has_view_permission(request, obj):
            raise PermissionDenied
        first = (
            obj.series.variants.filter(
                tubes=obj.tubes,
                sections__in=obj.allowed_sections,
                is_active=True,
            )
            .order_by('pk')
            .first()
        )
        form = ConnectionPreviewForm(
            request.GET or None,
            initial={'article': first.article if first else ''},
        )
        row = None
        if form.is_bound and form.is_valid():
            variants = obj.series.variants.filter(
                article=form.cleaned_data['article'], is_active=True
            )
            rows = (
                offer_query(variants)
                .with_execution(f'kzto-{obj.pk}')
                .page(1, 1)
            )
            if rows:
                from .offers import serialize_rows  # noqa: PLC0415

                row = serialize_rows(rows)[0]
        return TemplateResponse(
            request,
            'admin/catalog/connectionoption/preview.html',
            {
                **self.admin_site.each_context(request),
                'title': 'Расчёт подключения',
                'opts': self.model._meta,  # noqa: SLF001
                'option': obj,
                'form': form,
                'row': row,
            },
        )


@admin.register(ProductFamily)
class ProductFamilyAdmin(ModelAdmin):
    readonly_fields = ['presentation_photo']
    list_display = ['name', 'brand', 'category', 'key']
    list_filter = ['brand', 'category']
    search_fields = ['name', 'key', 'brand__name']
    autocomplete_fields = ['brand']


class ShowcaseInline(SortableInlineMixin, StackedInline):
    model = Showcase
    form = ImageModelForm
    extra = 0
    max_num = 1
    fields = [
        'image',
        'image_alt',
        'image_focus',
        'position',
    ]


@admin.register(Series)
class SeriesAdmin(InlineImagesAdminMixin, ModelAdmin):
    readonly_fields = ['pricing_mode', 'connections_link']
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
        'markup_percent',
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
        'family',
        'family_label',
        'factory_orientation',
        'pricing_mode',
        'connections_link',
        'subcategory',
        'name',
        'description',
        'markup_percent',
        'material',
        'heating',
        'pressure_bar',
        'warranty_years',
        'video',
        'is_published',
    ]

    @admin.display(description='Как получается цена')
    def pricing_mode(self, obj):
        if obj and obj.offer_mode == 'configured':
            return 'Цена базового радиатора + доплата выбранного подключения. Правила — по ссылке ниже.'
        return 'Цена и подключение указаны в прайсовых вариантах. Отдельные правила доплат не используются.'

    @admin.display(description='Где изменить подключение и цену')
    def connections_link(self, obj):
        if not obj or not obj.pk:
            return 'Сначала сохраните серию'
        configured = obj.offer_mode == 'configured'
        return format_html(
            '<a href="{}?series__id__exact={}">{}</a>',
            reverse(
                'admin:catalog_connectionoption_changelist'
                if configured
                else 'admin:catalog_variant_changelist'
            ),
            obj.pk,
            'Правила подключений этой серии'
            if configured
            else 'Прайсовые варианты этой серии',
        )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and 'brand' in form.changed_data:
            # Variant.brand копируется из серии только в save(); кэш сбросит
            # сигнал сохранения серии
            obj.variants.update(brand=obj.brand)
        if change and {'brand', 'markup_percent'} & set(form.changed_data):
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
