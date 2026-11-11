from decimal import ROUND_HALF_UP, Decimal

from django.core.paginator import Paginator
from django.db.models import Min
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.views import PublicReadMixin

from . import filters, schema, serializers
from .models import Brand, Category, Color, LeadTime, Series, Variant

PAGE_SIZE = 24


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
        images = Series.objects.filter(pk__in=page_series).prefetch_related(
            'images'
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
