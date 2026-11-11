from decimal import ROUND_HALF_UP, Decimal

from django.core.paginator import Paginator
from django.db.models import Count, Min, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.views import PublicReadMixin

from . import filters, schema, serializers
from .choices import Connection
from .models import (
    Brand,
    Category,
    Color,
    ColorGroup,
    LeadTime,
    Series,
    SeriesImage,
    Variant,
)
from .pricing import in_color

PAGE_SIZE = 24
VARIANTS_PAGE_SIZE = 20


class CategoryListView(PublicReadMixin, generics.ListAPIView):
    queryset = Category.objects.filter(is_published=True)
    serializer_class = serializers.CategorySerializer


class BrandListView(PublicReadMixin, generics.ListAPIView):
    queryset = Brand.objects.filter(is_published=True)
    serializer_class = serializers.BrandSerializer


class LeadTimeListView(PublicReadMixin, generics.ListAPIView):
    queryset = LeadTime.objects.filter(
        brand__is_published=True
    ).select_related(
        'brand',
    )
    serializer_class = serializers.LeadTimeSerializer


def _whole_byn(value: Decimal | None) -> int | None:
    if value is None:
        return None
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def visible_variants(category: str | None = None):
    """Активные варианты опубликованных серий и брендов."""
    qs = Variant.objects.filter(
        is_active=True,
        series__is_published=True,
        series__brand__is_published=True,
        series__category__is_published=True,
    )
    if category:
        qs = qs.filter(series__category__slug=category)
    return qs


def _series_colors(series_ids) -> dict[int, list[dict]]:
    rows = (
        Color.objects.filter(color_groups__series__in=series_ids)
        .order_by('color_groups__position', 'code')
        .values(
            'code',
            'name',
            'hex',
            'color_groups__series_id',
        )
    )
    result: dict[int, list[dict]] = {}
    for row in rows:
        colors = result.setdefault(row['color_groups__series_id'], [])
        item = {k: row[k] for k in ('code', 'name', 'hex')}
        if item not in colors:
            colors.append(item)
    return result


def _cards(filtered) -> list[tuple]:
    """(серия, витрина | None, цена) на каждую подходящую карточку, ещё без
    фото и цветов."""
    rows = (
        filtered.order_by()
        .values('series_id', 'height_mm')
        .annotate(price=Min('price_byn'))
    )
    prices: dict[int, dict] = {}
    for row in rows:
        prices.setdefault(row['series_id'], {})[row['height_mm']] = row[
            'price'
        ]
    series_list = (
        Series.objects.filter(pk__in=prices)
        .select_related('brand')
        .prefetch_related('showcases__variant')
    )
    cards = []
    for series in series_list:
        by_height = prices[series.pk]
        known = [p for p in by_height.values() if p is not None]
        series_price = min(known) if known else None
        showcases = [
            sc
            for sc in series.showcases.all()
            if sc.variant is None
            or sc.variant.height_mm is None
            or sc.variant.height_mm in by_height
        ]
        if not showcases:
            cards.append((series, None, series_price))
            continue
        for showcase in showcases:
            height = showcase.variant.height_mm if showcase.variant else None
            price = by_height.get(height) if height is not None else None
            if height is None:
                price = series_price
            cards.append((series, showcase, price))
    # Без цены — в конец; остальной порядок — как задан в админке
    cards.sort(
        key=lambda c: (
            c[2] is None,
            c[0].position,
            c[0].pk,
            c[1].position if c[1] else 0,
            c[1].pk if c[1] else 0,
        )
    )
    return cards


class SeriesListView(PublicReadMixin, APIView):
    def get(self, request):
        category = request.query_params.get('category') or None
        fields = schema.for_category(category)
        parsed = filters.parse(request.query_params, fields)
        base = visible_variants(category)
        filtered = filters.apply(base, parsed)
        brands = [
            slug
            for part in request.query_params.get('brand', '').split(',')
            if (slug := part.strip())
        ]

        paginator = Paginator(_cards(filtered), PAGE_SIZE)
        page = paginator.get_page(request.query_params.get('page'))
        page_series = {c[0].pk for c in page.object_list}
        images = (
            Series.objects.filter(pk__in=page_series)
            .select_related('brand')
            .prefetch_related('images')
        )
        by_id = {s.pk: s for s in images}
        colors = _series_colors(page_series)
        results = [
            serializers.card(
                by_id[series.pk],
                showcase,
                _whole_byn(price),
                colors.get(series.pk, []),
            )
            for series, showcase, price in page.object_list
        ]
        return Response(
            {
                'count': paginator.count,
                'results': results,
                'facets': filters.facets(base, fields, parsed),
                'model_range': self.model_range(category, brands),
            }
        )

    @staticmethod
    def model_range(category, brands):
        if not brands:
            return []
        series = (
            Series.objects.filter(
                is_published=True,
                brand__is_published=True,
                category__is_published=True,
                brand__slug__in=brands,
            )
            .select_related('brand')
            .prefetch_related('images')
        )
        if category:
            series = series.filter(category__slug=category)
        return [serializers.tile(s) for s in series]


def _series_fields(series) -> list[schema.Field]:
    """Схема категории без бренда: внутри серии он один."""
    return [
        f
        for f in schema.for_category(series.category.slug)
        if f.key != 'brand'
    ]


def _published_series(slug: str) -> Series:
    series = get_object_or_404(
        Series.objects.filter(
            is_published=True,
            brand__is_published=True,
            category__is_published=True,
        )
        .select_related('brand', 'category')
        .prefetch_related(
            Prefetch(
                'images',
                queryset=SeriesImage.objects.select_related('color'),
            ),
            'files',
            Prefetch(
                'color_groups',
                queryset=ColorGroup.objects.prefetch_related('colors'),
            ),
        ),
        slug=slug,
    )
    return series


def _executions(variants) -> list[dict]:
    order = [str(value) for value in Connection.values]
    labels = dict(Connection.choices)
    rows = (
        variants.order_by()
        .values('tubes', 'connection')
        .annotate(count=Count('pk'))
    )
    merged: dict[tuple[int, str], int] = {}
    for row in rows:
        key = (row['tubes'] or 0, row['connection'])
        merged[key] = merged.get(key, 0) + row['count']
    result = []
    for (tubes, connection), count in merged.items():
        parts = []
        if tubes:
            parts.append(f'{tubes}-трубный')
        if connection:
            parts.append(str(labels.get(connection, connection)))
        result.append(
            {
                'key': f'{tubes}-{connection}',
                'tubes': tubes,
                'connection': connection,
                'label': ', '.join(parts) or 'Стандартное',
                'count': count,
            }
        )
    result.sort(
        key=lambda e: (
            -e['count'],
            -e['tubes'],
            order.index(e['connection'])
            if e['connection'] in order
            else len(order),
            e['connection'],
        )
    )
    return result


class SeriesDetailView(PublicReadMixin, APIView):
    def get(self, request, slug):  # noqa: ARG002
        series = _published_series(slug)
        fields = _series_fields(series)
        variants = visible_variants().filter(series=series)
        ranges = {
            key: [facet['min'], facet['max']]
            for key, facet in filters.range_facets(variants, fields).items()
        }
        return Response(
            serializers.series_detail(
                series,
                ranges=ranges,
                executions=_executions(variants),
                columns=[
                    f for f in fields if f.column and f.kind != schema.COLORS
                ],
                filters=[f for f in fields if f.filter],
            )
        )


def _available_groups(variant, groups: dict[int, ColorGroup]):
    """Группы цветов варианта; пустой список — все группы серии."""
    explicit = [
        groups[g.pk] for g in variant.color_groups.all() if g.pk in groups
    ]
    return explicit or list(groups.values())


def _variant_price(variant, groups: dict[int, ColorGroup], color):
    """Цена в группе выбранного цвета; цвета нет у варианта — None. Без цвета:
    базовая группа, если она доступна варианту, иначе самая дешёвая из
    доступных (не any_ral); у серии без групп — цена варианта."""
    if not groups:
        return _whole_byn(variant.price_byn)
    available = _available_groups(variant, groups)
    if color:
        group = next(
            (
                g
                for g in available
                if any(c.code == color for c in g.colors.all())
            ),
            None,
        )
    else:
        group = next((g for g in available if g.is_base), None)
        if group is None:
            group = min(
                (g for g in available if not g.any_ral),
                key=lambda g: g.percent,
                default=None,
            )
    return None if group is None else in_color(variant.price_byn, group)


def _selected_color(parsed: dict) -> str | None:
    entry = parsed.get(filters.COLOR_KEY)
    return entry[2][0] if entry else None


def _series_variants(series):
    return visible_variants().filter(series=series)


class SeriesVariantsView(PublicReadMixin, APIView):
    def get(self, request, slug):
        series = _published_series(slug)
        fields = _series_fields(series)
        params = request.query_params.copy()
        # Цвет один: из списка берём первый
        raw = params.get(filters.COLOR_KEY, '')
        params[filters.COLOR_KEY] = raw.split(',')[0].strip()
        parsed = filters.parse(params, fields)
        base = _series_variants(series)
        filtered = filters.apply(base, parsed)
        wanted = request.query_params.get(filters.EXECUTION_KEY, '').strip()
        if wanted and filters.EXECUTION_KEY not in parsed:
            # Непонятное исполнение — пустая таблица, а не вся серия
            filtered = filtered.none()
        filtered = filtered.order_by('height_mm', 'width_mm', 'power_w', 'pk')
        filtered = filtered.prefetch_related('color_groups')

        if request.query_params.get('page') == 'all':
            variants = list(filtered)
            count = len(variants)
        else:
            paginator = Paginator(filtered, VARIANTS_PAGE_SIZE)
            variants = list(
                paginator.get_page(request.query_params.get('page'))
            )
            count = paginator.count
        groups = {g.pk: g for g in series.color_groups.all()}
        color = _selected_color(parsed)
        return Response(
            {
                'count': count,
                'results': [
                    serializers.row(v, _variant_price(v, groups, color))
                    for v in variants
                ],
                'facets': filters.facets(base, fields, parsed),
            }
        )


class VariantDetailView(PublicReadMixin, APIView):
    def get(self, request, article):
        slug = request.query_params.get('series', '')
        series = _published_series(slug)
        variant = get_object_or_404(
            _series_variants(series).prefetch_related('color_groups'),
            article=article,
        )
        groups = {g.pk: g for g in series.color_groups.all()}
        color = request.query_params.get('color') or None
        data = serializers.row(variant, _variant_price(variant, groups, color))
        data['available_groups'] = [
            g.pk for g in _available_groups(variant, groups)
        ]
        return Response(data)
