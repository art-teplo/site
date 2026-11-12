from django.core.paginator import Paginator
from django.db.models import Case, Count, Min, Prefetch, Q, When
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.models import Project
from apps.content.serializers import ProjectSerializer
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
    Subcategory,
    Variant,
)
from .pricing import (
    available_groups,
    base_price,
    in_color,
    price_from,
    whole_byn,
)

PAGE_SIZE = 24
# Сортировка списка: по цене «от» карточки; без параметра — порядок из админки
SORTS = {'price', '-price'}
SIMILAR_MAX = 4
SEARCH_MAX = 20
SEARCH_MIN_LENGTH = 2
VARIANTS_PAGE_SIZE = 20
ALL_ROWS_MAX = 500  # потолок для page=all


class CategoryListView(PublicReadMixin, generics.ListAPIView):
    queryset = (
        Category.objects.filter(is_published=True)
        .annotate(
            series_count=Count('series', filter=Q(series__is_published=True)),
        )
        .prefetch_related(
            Prefetch(
                'types',
                queryset=Subcategory.objects.filter(is_published=True)
                .annotate(
                    series_count=Count(
                        'series',
                        filter=Q(series__is_published=True),
                    ),
                )
                .order_by('position', 'pk'),
            ),
        )
        .order_by('position', 'pk')
    )
    serializer_class = serializers.CategorySerializer


class BrandListView(PublicReadMixin, generics.ListAPIView):
    queryset = (
        Brand.objects.filter(is_published=True)
        .annotate(
            series_count=Count('series', filter=Q(series__is_published=True)),
        )
        .order_by('position', 'pk')
    )
    serializer_class = serializers.BrandSerializer


class LeadTimeListView(PublicReadMixin, generics.ListAPIView):
    queryset = LeadTime.objects.filter(
        brand__is_published=True
    ).select_related(
        'brand',
    )
    serializer_class = serializers.LeadTimeSerializer


def visible_variants(
    category: str | None = None,
    subcategory: str | None = None,
):
    """Активные варианты опубликованных серий и брендов."""
    qs = Variant.objects.filter(
        is_active=True,
        series__is_published=True,
        series__brand__is_published=True,
        series__category__is_published=True,
    )
    if category:
        qs = qs.filter(series__category__slug=category)
    if subcategory:
        qs = qs.filter(series__subcategory__slug=subcategory)
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


def _render_cards(cards: list[tuple]) -> list[dict]:
    """JSON карточек из (серия, витрина, цена): фото и цвета — пачкой."""
    series_ids = {c[0].pk for c in cards}
    by_id = {
        s.pk: s
        for s in Series.objects.filter(pk__in=series_ids)
        .select_related('brand', 'category', 'subcategory')
        .prefetch_related('images')
    }
    colors = _series_colors(series_ids)
    return [
        serializers.card(
            by_id[series.pk],
            showcase,
            price,
            colors.get(series.pk, []),
        )
        for series, showcase, price in cards
    ]


def _cards(filtered) -> list[tuple]:
    """(серия, витрина | None, цена) на каждую подходящую карточку, ещё без
    фото и цветов."""
    # Варианты без своих групп цвета — одним запросом, минимум по цене (в
    # любой группе серии процент монотонен); с явными группами — по одному.
    plain = (
        filtered.filter(color_groups__isnull=True)
        .order_by()
        .values('series_id', 'height_mm')
        .annotate(price=Min('price_byn'))
    )
    explicit = (
        filtered.filter(color_groups__isnull=False)
        .distinct()
        .prefetch_related('color_groups')
    )
    series_ids = {r['series_id'] for r in plain} | {
        v.series_id for v in explicit
    }
    groups: dict[int, dict[int, ColorGroup]] = {}
    for group in ColorGroup.objects.filter(series_id__in=series_ids):
        groups.setdefault(group.series_id, {})[group.pk] = group
    offers: dict[int, dict] = {}
    for row in plain:
        available = list(groups.get(row['series_id'], {}).values())
        offers.setdefault(row['series_id'], {}).setdefault(
            row['height_mm'], []
        ).append((row['price'], available))
    for variant in explicit:
        available = available_groups(
            variant, groups.get(variant.series_id, {})
        )
        offers.setdefault(variant.series_id, {}).setdefault(
            variant.height_mm, []
        ).append((variant.price_byn, available))
    prices = {
        series_id: {h: price_from(o) for h, o in by_height.items()}
        for series_id, by_height in offers.items()
    }
    series_list = (
        Series.objects.filter(pk__in=prices)
        .select_related('brand', 'category', 'subcategory')
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
        subcategory = request.query_params.get('type') or None
        fields = schema.for_category(category)
        parsed = filters.parse(request.query_params, fields)
        base = visible_variants(category, subcategory)
        filtered = filters.apply(base, parsed)
        brands = [
            slug
            for part in request.query_params.get('brand', '').split(',')
            if (slug := part.strip())
        ]

        cards = _cards(filtered)
        sort = request.query_params.get('sort')
        if sort in SORTS:
            # «По запросу» — всегда в конце; при равной цене — порядок админки
            sign = -1 if sort.startswith('-') else 1
            cards.sort(key=lambda c: (c[2] is None, sign * (c[2] or 0)))
        paginator = Paginator(cards, PAGE_SIZE)
        page = paginator.get_page(request.query_params.get('page'))
        results = _render_cards(page.object_list)
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


def _similar(series: Series) -> list[dict]:
    """До 8 карточек: та же категория, сначала тот же тип."""
    candidates = list(
        Series.objects.filter(
            is_published=True,
            brand__is_published=True,
            category=series.category_id,
        )
        .exclude(pk=series.pk)
        .order_by('position', 'pk')
        .values_list('pk', 'subcategory_id')
    )
    same = series.subcategory_id is not None
    # С запасом: у части серий нет вариантов в продаже и карточки не будет
    candidates.sort(key=lambda c: not (same and c[1] == series.subcategory_id))
    ids = [pk for pk, _ in candidates[: SIMILAR_MAX * 2]]
    rank = {pk: i for i, pk in enumerate(ids)}
    cards = _cards(visible_variants().filter(series_id__in=ids))
    first: dict[int, tuple] = {}
    for card in cards:
        first.setdefault(card[0].pk, card)
    chosen = sorted(
        first.values(),
        key=lambda c: (c[2] is None, rank[c[0].pk]),
    )
    return _render_cards(chosen[:SIMILAR_MAX])


def _projects(series: Series) -> list[dict]:
    projects = Project.objects.filter(
        is_published=True,
        series=series,
    ).prefetch_related('photos', 'series')
    return ProjectSerializer(projects, many=True).data


class SearchView(PublicReadMixin, APIView):
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < SEARCH_MIN_LENGTH:
            return Response([])
        found = Series.objects.filter(
            Q(name__icontains=query)
            | Q(brand__name__icontains=query)
            | Q(subcategory__name__icontains=query)
            | Q(category__name__icontains=query)
            | Q(variants__article__iexact=query)
        )
        cards = _cards(
            visible_variants().filter(series__in=found.values('pk'))
        )
        return Response(_render_cards(cards[:SEARCH_MAX]))


class SeriesDetailView(PublicReadMixin, APIView):
    def get(self, request, slug):  # noqa: ARG002
        series = _published_series(slug)
        fields = _series_fields(series)
        variants = visible_variants().filter(series=series)
        ranges = {
            key: [facet['min'], facet['max']]
            for key, facet in filters.range_facets(variants, fields).items()
        }
        groups = {g.pk: g for g in series.color_groups.all()}
        # Как в _cards: варианты без своих групп — одним агрегатом, в Python
        # грузим только варианты с явными группами.
        plain = variants.filter(color_groups__isnull=True).aggregate(
            price=Min('price_byn')
        )['price']
        offers = [(plain, list(groups.values()))] if plain is not None else []
        offers += [
            (v.price_byn, available_groups(v, groups))
            for v in variants.filter(color_groups__isnull=False)
            .distinct()
            .prefetch_related('color_groups')
        ]
        return Response(
            serializers.series_detail(
                series,
                ranges=ranges,
                price_from=price_from(offers),
                price_from_by_group={
                    g.pk: price_from(offers, g) for g in groups.values()
                },
                executions=_executions(variants),
                columns=[
                    f for f in fields if f.column and f.kind != schema.COLORS
                ],
                filters=[f for f in fields if f.filter],
                similar=_similar(series),
                projects=_projects(series),
            )
        )


def _variant_price(variant, groups: dict[int, ColorGroup], color):
    """Цена в группе выбранного цвета; цвета нет у варианта — None. Без цвета —
    pricing.base_price."""
    if not groups:
        return whole_byn(variant.price_byn)
    available = available_groups(variant, groups)
    if not color:
        return base_price(variant.price_byn, available)
    group = next(
        (g for g in available if any(c.code == color for c in g.colors.all())),
        None,
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
            count = filtered.count()
            variants = list(filtered[:ALL_ROWS_MAX])
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
        found = _series_variants(series).prefetch_related('color_groups')
        found = found.filter(article=article)
        connection = request.query_params.get('connection')
        if connection:
            found = found.filter(connection=connection)
        # Без подключения: боковое («стоя»), иначе первый по размерам
        found = found.order_by(
            Case(When(connection=Connection.SIDE, then=0), default=1),
            'height_mm',
            'width_mm',
        )
        variant = found.first()
        if variant is None:
            raise Http404
        groups = {g.pk: g for g in series.color_groups.all()}
        color = request.query_params.get('color') or None
        data = serializers.row(variant, _variant_price(variant, groups, color))
        data['available_groups'] = [
            g.pk for g in available_groups(variant, groups)
        ]
        return Response(data)
