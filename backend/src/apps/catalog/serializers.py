import math

from rest_framework import serializers

from apps.content.serializers import ImageAssetMixin, image_asset

from . import schema
from .models import Brand, Category, LeadTime, SeriesImage
from .pricing import effective_percent


class CategorySerializer(ImageAssetMixin, serializers.ModelSerializer):
    series_count = serializers.IntegerField(read_only=True)
    types = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['slug', 'name', 'short', 'image', 'series_count', 'types']

    def get_types(self, obj):
        # Опубликованные типы с series_count — prefetch в CategoryListView
        return [
            {
                'slug': t.slug,
                'name': t.name,
                'image': image_asset(t) if t.image else None,
                'series_count': t.series_count,
            }
            for t in obj.types.all()
        ]


class BrandSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    series_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Brand
        fields = [
            'slug',
            'name',
            'country',
            'note',
            'logo',
            'warranty_years',
            'series_count',
        ]

    def get_logo(self, obj):
        return obj.logo.url if obj.logo else None


class LeadTimeSerializer(serializers.ModelSerializer):
    brand = serializers.SlugRelatedField(slug_field='slug', read_only=True)

    class Meta:
        model = LeadTime
        fields = ['series', 'brand', 'days', 'updated_at']


# Витрину без ориентации от этой высоты считаем вертикальной
VERTICAL_FROM_MM = 900


def _orientation(variant) -> str:
    """h / v варианта витрины: из поля, иначе по высоте; неизвестно — ''."""
    if variant is None:
        return ''
    if variant.orientation:
        return variant.orientation
    # По высоте, а не по пропорциям: витрина стоит на самом маленьком
    # варианте, и низкий радиатор на 4 секции выходит «выше, чем шире»
    if variant.height_mm:
        return 'v' if variant.height_mm >= VERTICAL_FROM_MM else 'h'
    return ''


def _card_photo(showcase, series):
    """Фото серии для карточки витрины без своего фото: той же ориентации,
    что вариант витрины (низкий и высокий формфактор одной серии не
    выглядят одинаково), «товарное» раньше «в интерьере»; иначе главное."""
    images = list(series.images.all())
    orientation = _orientation(showcase.variant if showcase else None)
    if orientation:
        same = [i for i in images if i.orientation == orientation]
        same.sort(key=lambda i: i.kind != SeriesImage.Kind.PRODUCT)
        if same:
            return same[0]
    # Формфактор не задан: карточка вертикальная (4:5) — товарное фото,
    # которое ближе к ней по форме, иначе главное. Горизонтальное фото в
    # вертикальной рамке теряло ~40 % кадра и выглядело «зазумленным»
    product = [i for i in images if i.kind == SeriesImage.Kind.PRODUCT]
    if product:
        return min(product, key=_card_misfit)
    return _main_image(series)


CARD_RATIO = 4 / 5


def _card_misfit(image):
    """Насколько фото не совпадает по форме с карточкой: 0 — точно.
    Без размеров — в конец, порядок из админки сохраняется (min стабилен)."""
    if not image.image_width or not image.image_height:
        return math.inf
    return abs(math.log(image.image_width / image.image_height / CARD_RATIO))


def card_image(showcase, series):
    """Фото витрины, иначе фото серии под её формфактор, иначе None."""
    if showcase is not None and showcase.image:
        return image_asset(showcase)
    image = _card_photo(showcase, series)
    return image_asset(image) if image is not None else None


def _main_image(series):
    """Главное фото серии: первое «товарное», иначе первое любое."""
    images = list(series.images.all())
    product = [i for i in images if i.kind == SeriesImage.Kind.PRODUCT]
    return (product or images or [None])[0]


def series_image(series):
    image = _main_image(series)
    return image_asset(image) if image is not None else None


def hover_image(series, showcase=None):
    """Фото при наведении: первое «в интерьере», иначе второе «товарное»;
    не то же, что уже стоит в карточке."""
    shown = (
        None
        if showcase and showcase.image
        else _card_photo(
            showcase,
            series,
        )
    )
    images = [i for i in series.images.all() if i != shown]
    interior = [i for i in images if i.kind == SeriesImage.Kind.INTERIOR]
    product = [i for i in images if i.kind == SeriesImage.Kind.PRODUCT]
    if interior:
        return image_asset(interior[0])
    if shown is None and len(product) > 1:
        return image_asset(product[1])
    return image_asset(product[0]) if product and shown else None


def card(series, showcase, price, colors):
    """Карточка списка: серия в одном формфакторе."""
    variant = showcase.variant if showcase is not None else None
    return {
        'series': series.slug,
        'name': series.name,
        'brand': series.brand.slug,
        'category': series.category.slug,
        'label': showcase.label if showcase is not None else '',
        'height_mm': variant.height_mm if variant is not None else None,
        'price_from': price,
        'image': card_image(showcase, series),
        'hover_image': hover_image(series, showcase),
        'type': series.subcategory.slug if series.subcategory else None,
        'colors': colors,
    }


def tile(series):
    """Плитка модельного ряда бренда."""
    return {
        'series': series.slug,
        'name': series.name,
        'image': series_image(series),
    }


def field(item: schema.Field) -> dict:
    return {
        'key': item.key,
        'label': item.label,
        'kind': item.kind,
        'unit': item.unit,
    }


def color_group(group) -> dict:
    return {
        'id': group.pk,
        'name': group.name,
        'percent': effective_percent(group),
        'is_base': group.is_base,
        'any_ral': group.any_ral,
        'colors': [
            {
                'code': color.code,
                'name': color.name,
                'hex': color.hex,
                'finish': color.finish,
            }
            for color in group.colors.all()
        ],
    }


def series_image_full(image) -> dict:
    return {
        **image_asset(image),
        'color': image.color.code if image.color else None,
        'kind': image.kind,
        'orientation': image.orientation,
    }


def series_detail(
    series,
    *,
    ranges: dict,
    price_from: int | None,
    price_from_by_group: dict[int, int | None],
    executions: list[dict],
    columns: list[schema.Field],
    filters: list[schema.Field],
    similar: list[dict],
    projects: list[dict],
) -> dict:
    return {
        'slug': series.slug,
        'name': series.name,
        'category': series.category.slug,
        'brand': {
            'slug': series.brand.slug,
            'name': series.brand.name,
            'country': series.brand.country,
        },
        'description': series.description,
        'material': series.material,
        'heating': series.heating,
        'pressure_bar': series.pressure_bar,
        'warranty_years': series.warranty,
        'video_url': series.video_url,
        'images': [series_image_full(i) for i in series.images.all()],
        'files': [
            {'title': f.title, 'url': f.file.url} for f in series.files.all()
        ],
        'color_groups': [color_group(g) for g in series.color_groups.all()],
        'ranges': ranges,
        'price_from': price_from,
        'price_from_by_group': price_from_by_group,
        'executions': executions,
        'default_execution': executions[0]['key'] if executions else None,
        'columns': [field(f) for f in columns],
        'filters': [field(f) for f in filters],
        'similar': similar,
        'projects': projects,
    }


def row(variant, price: int | None) -> dict:
    return {
        'article': variant.article,
        'height_mm': variant.height_mm,
        'width_mm': variant.width_mm,
        'depth_mm': variant.depth_mm,
        'length_mm': variant.length_mm,
        'axis_mm': variant.axis_mm,
        'sections': variant.sections,
        'power_w': variant.power_w,
        'area_m2': (
            round(variant.power_w / schema.WATTS_PER_M2, 1)
            if variant.power_w is not None
            else None
        ),
        'tubes': variant.tubes,
        'connection': variant.connection,
        'thermovalve': variant.thermovalve,
        'orientation': variant.orientation,
        'mount': variant.mount,
        'attrs': variant.attrs,
        'price': price,
        # Цена без цвета и группы варианта: фронт пересчитывает цену при
        # смене цвета сразу, не дожидаясь ответа (lib/price.ts rowPrice)
        'price_byn': (
            float(variant.price_byn) if variant.price_byn is not None else None
        ),
        'color_groups': [g.pk for g in variant.color_groups.all()],
    }
