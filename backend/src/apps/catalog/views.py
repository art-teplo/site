from django.core.paginator import Paginator
from django.db.models import Count, Max, Min, Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.models import Project
from apps.content.serializers import ProjectSerializer
from apps.content.views import PublicReadMixin

from . import filters, schema, search, serializers
from . import offers as offers_service
from .choices import Orientation
from .importers.factory_editions import legacy_targets
from .importers.kzto_series import LEGACY_SERIES as KZTO_LEGACY_SERIES
from .importers.product_families import radimax_legacy_targets
from .models import (
    Brand,
    Category,
    Color,
    ColorGroup,
    LeadTime,
    LegacyColorAlias,
    Series,
    SeriesImage,
    Subcategory,
    Variant,
)
from .pricing import (
    available_groups,
    base_price,
    in_color,
    whole_byn,
)

LEGACY_SERIES = {
    **KZTO_LEGACY_SERIES,
    **legacy_targets(),
    **radimax_legacy_targets(),
}

PAGE_SIZE = 24
# Два явных направления сортировки по цене «от» карточки.
SORTS = {'price', '-price'}
SIMILAR_MAX = 4
SEARCH_MAX = 20
SEARCH_MIN_LENGTH = 2
SEARCH_MAX_QUERY = 100
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
    for series_id in (
        ColorGroup.objects.filter(series_id__in=series_ids, any_ral=True)
        .values_list('series_id', flat=True)
        .distinct()
    ):
        result.setdefault(series_id, []).append(
            {
                'code': 'any-ral',
                'name': 'Любой RAL — по запросу',
                'hex': 'conic-gradient(var(--color-accent), var(--color-cream-paper), var(--color-near-black), var(--color-accent))',
            }
        )
    return result


def _auto_labels(series_ids) -> dict[int, str]:
    """Подпись из вариантов серии: «Вертикальный,
    200–2500 мм»; оба положения или ни одного — «Высота 334–2034 мм»."""
    rows = (
        Variant.objects.filter(series_id__in=series_ids, is_active=True)
        .order_by()
        .values('series_id', 'series__factory_orientation')
        .annotate(
            low=Min('height_mm'),
            high=Max('height_mm'),
            h=Count('pk', filter=Q(orientation=Orientation.HORIZONTAL)),
            v=Count('pk', filter=Q(orientation=Orientation.VERTICAL)),
        )
    )
    labels = {}
    for row in rows:
        factory = row['series__factory_orientation']
        positions = [o.label for o in Orientation if row[o.value]]
        position = (
            Orientation(factory).label
            if factory
            else positions[0]
            if len(positions) == 1
            else ''
        )
        height = None
        if row['low'] is not None:
            same = row['low'] == row['high']
            height = (
                f'{row["low"]} мм'
                if same
                else f'{row["low"]}–{row["high"]} мм'
            )
        if position:
            text = ', '.join(filter(None, [position.capitalize(), height]))
        else:
            text = f'Высота {height}' if height else ''
        labels[row['series_id']] = text
    return labels


def _render_cards(cards: list[tuple]) -> list[dict]:
    """JSON карточек из (серия, витрина, цена): фото, цвета и подписи —
    пачкой."""
    series_ids = {c[0].pk for c in cards}
    labels = _auto_labels(series_ids)
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
            labels.get(series.pk, ''),
        )
        for series, showcase, price in cards
    ]


def _cards(filtered) -> list[tuple]:
    """(серия, витрина | None, цена) на каждую подходящую карточку, ещё без
    фото и цветов."""
    query = (
        filtered
        if isinstance(filtered, offers_service.OfferQuery)
        else offers_service.offer_query(filtered)
    )
    prices = {
        row['series_id']: row['price']
        for row in query.select(
            'series_id, MIN(price) AS price', suffix='GROUP BY series_id'
        )
    }
    series_list = (
        Series.objects.filter(pk__in=prices)
        .select_related('brand', 'category', 'subcategory')
        .prefetch_related('showcases')
    )
    cards = []
    for series in series_list:
        showcase = next(
            (sc for sc in series.showcases.all() if sc.image), None
        )
        cards.append((series, showcase, prices[series.pk]))
    # Без цены — в конец; остальной порядок — как задан в админке
    cards.sort(
        key=lambda c: (
            c[2] is None,
            c[0].position,
            c[0].pk,
        )
    )
    return cards


def _sorted(cards: list[tuple], sort: str | None) -> list[tuple]:
    """?sort=price / -price — по цене «от»; «по запросу» всегда в конце, при
    равной цене — порядок админки. Без параметра — порядок админки."""
    if sort in SORTS:
        sign = -1 if sort.startswith('-') else 1
        cards.sort(key=lambda c: (c[2] is None, sign * (c[2] or 0)))
    return cards


def _popular_catalog_order(cards: list[tuple]) -> list[tuple]:
    # Линейка занимает место первого исполнения в исходном порядке админки.
    family_order = {}
    for index, (series, _, price) in enumerate(cards):
        if series.family_id:
            family_order.setdefault((price is None, series.family_id), index)

    def key(entry):
        index, (series, _, price) = entry
        missing_price = price is None
        return (
            missing_price,
            series.brand.position,
            series.brand_id,
            family_order.get((missing_price, series.family_id), index),
        )

    return [card for _, card in sorted(enumerate(cards), key=key)]


class SeriesListView(PublicReadMixin, APIView):
    def get(self, request):
        category = request.query_params.get('category') or None
        subcategory = request.query_params.get('type') or None
        fields = schema.for_category(category)
        parsed = filters.parse(request.query_params, fields)
        base = visible_variants(category, subcategory)
        filtered = offers_service.offer_query(
            base, color=_selected_color(parsed), bulk=True
        ).filter(parsed)
        if request.query_params.get('execution') and 'execution' not in parsed:
            filtered = filtered.with_execution(
                request.query_params['execution']
            )
        cards_only = request.query_params.get('cards_only') == '1'
        with offers_service.catalog_query_plan():
            cards = _cards(filtered)
            facets = [] if cards_only else filtered.facets(fields)
        sort = request.query_params.get('sort')
        cards = (
            _sorted(cards, sort)
            if sort in SORTS
            else _popular_catalog_order(cards)
        )
        paginator = Paginator(cards, PAGE_SIZE)
        page = paginator.get_page(request.query_params.get('page'))
        data = {
            'count': paginator.count,
            'results': _render_cards(page.object_list),
        }
        if cards_only:
            return Response(data)

        brands = [
            slug
            for part in request.query_params.get('brand', '').split(',')
            if (slug := part.strip())
        ]
        return Response(
            {
                **data,
                'facets': facets,
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
            .select_related('brand', 'family__presentation_photo')
            .prefetch_related('images')
        )
        if category:
            series = series.filter(category__slug=category)
        result, seen = [], set()
        for s in series:
            if s.family_id and s.family.presentation_photo_id:
                if s.family_id in seen:
                    continue
                seen.add(s.family_id)
            result.append(serializers.tile(s))
        return result


def _series_fields(series) -> list[schema.Field]:
    """Схема категории без бренда: внутри серии он один."""
    return [
        f
        for f in schema.for_category(series.category.slug)
        if f.key != 'brand'
    ]


def _published_series(slug: str, *, media=True) -> Series:
    query = Series.objects.filter(
        is_published=True,
        brand__is_published=True,
        category__is_published=True,
    ).select_related('brand', 'category', 'family__presentation_photo')
    if media:
        query = query.prefetch_related(
            Prefetch(
                'images',
                queryset=SeriesImage.objects.select_related('color'),
            ),
            'files',
            Prefetch(
                'color_groups',
                queryset=ColorGroup.objects.prefetch_related('colors'),
            ),
        )
    return get_object_or_404(query, slug=slug)


def _executions(variants) -> list[dict]:
    return offers_service.execution_metadata(
        offers_service.offer_query(variants)
    )


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
    """Поиск: слова запроса в названии, бренде, типе, категории или артикул;
    другая раскладка и синонимы (search.py). ?sort= — как у списка,
    ?limit= — для подсказок под полем (не больше SEARCH_MAX)."""

    def get(self, request):
        query = request.query_params.get('q', '').strip()[:SEARCH_MAX_QUERY]
        where = search.series_filter(query)
        if len(query) < SEARCH_MIN_LENGTH or where is None:
            return Response([])
        # Готовый список id: подзапрос внутри выборки вариантов Postgres
        # планировал плохо. Серий — десятки, список короткий
        found = list(Series.objects.filter(where).values_list('pk', flat=True))
        cards = _sorted(
            _cards(visible_variants().filter(series__in=found)),
            request.query_params.get('sort'),
        )
        try:
            limit = int(request.query_params.get('limit', SEARCH_MAX))
        except ValueError:
            limit = SEARCH_MAX
        limit = max(1, min(limit, SEARCH_MAX))
        return Response(_render_cards(cards[:limit]))


class SeriesDetailView(PublicReadMixin, APIView):
    def get(self, request, slug):  # noqa: ARG002
        series = _published_series(slug)
        fields = _series_fields(series)
        variants = visible_variants().filter(series=series)
        query = offers_service.offer_query(variants)
        ranges = {
            key: [f['min'], f['max']]
            for key, f in query.range_facets(fields).items()
        }
        groups = {g.pk: g for g in series.color_groups.all()}
        by_group = {
            g.pk: (
                None
                if g.any_ral
                else offers_service.offer_query(
                    variants, group_id=g.pk
                ).price_bounds()[0]
            )
            for g in groups.values()
        }
        return Response(
            serializers.series_detail(
                series,
                ranges=ranges,
                range_steps=filters.range_steps(variants, fields),
                price_from=query.price_bounds()[0],
                price_from_by_group=by_group,
                executions=offers_service.execution_metadata(query),
                columns=[
                    f for f in fields if f.column and f.kind != schema.COLORS
                ],
                filters=[f for f in fields if f.filter],
                similar=_similar(series),
                projects=_projects(series),
            )
        )


def _legacy_color(parent_slug, series, color):
    if color and color.startswith('any-') and color[4:].isdigit():
        alias = (
            LegacyColorAlias.objects.filter(
                parent_slug=parent_slug,
                old_group_id=int(color[4:]),
                group__series=series,
                group__any_ral=True,
            )
            .values_list('group_id', flat=True)
            .first()
        )
        if alias is not None:
            return f'any-{alias}'
        old = ColorGroup.objects.filter(
            pk=int(color[4:]), series__slug=parent_slug, any_ral=True
        ).first()
        new = (
            series.color_groups.filter(legacy_origin=old, any_ral=True).first()
            if old
            else None
        )
        return f'any-{new.pk}' if new else color

    return color


def _legacy_choice_queries(parent_slug, targets, params):
    result = {}
    for series in Series.objects.filter(slug__in=targets):
        query = params.copy()
        color = _legacy_color(parent_slug, series, params.get('color'))
        if color:
            query['color'] = color
        article = query.get('v')
        if (
            article
            and not series.variants.filter(
                article=article, is_active=True
            ).exists()
        ):
            query.pop('v', None)
        result[series.slug] = query.urlencode()
    return result


class LegacySeriesView(PublicReadMixin, APIView):
    def get(self, request, slug):
        targets = LEGACY_SERIES.get(slug)
        if targets is None:
            raise Http404
        variants = visible_variants().filter(
            series__slug__in=targets, series__brand__slug=slug.split('-')[0]
        )
        choices = _render_cards(
            list({c[0].pk: c for c in _cards(variants)}.values())
        )
        article = request.query_params.get('v')
        fields = schema.for_category('radiatory')
        parsed = filters.parse(request.query_params, fields)
        parsed.pop('color', None)
        resolution = offers_service.offer_query(variants).filter(parsed)
        key = request.query_params.get('execution', '')
        if key and 'execution' not in parsed:
            resolution = resolution.with_execution(key)
        if article:
            resolution = offers_service.offer_query(
                variants.filter(article=article)
            ).filter(parsed)
            if key and 'execution' not in parsed:
                resolution = resolution.with_execution(key)
        variants = variants.filter(series_id__in=resolution.series_ids())
        matches = (
            list(
                variants.filter(article=article)
                .values_list('series__slug', flat=True)
                .distinct()
            )
            if article
            else []
        )
        target = matches[0] if len(matches) == 1 else None
        execution, color = None, request.query_params.get('color')
        if target:
            variant = (
                variants.select_related('series')
                .filter(article=article, series__slug=target)
                .first()
            )
            explicit = request.query_params.get('execution')
            if explicit:
                execution = explicit
            else:
                query, _fields = offers_service.query_for_series(
                    variant.series,
                    request.query_params,
                    detail=True,
                    variants=variants.filter(
                        series__slug=target, article=article
                    ),
                )
                choices_for_article = offers_service.execution_metadata(query)
                execution = (
                    choices_for_article[0]['key']
                    if choices_for_article
                    else None
                )
            color = _legacy_color(slug, variant.series, color)
        return Response(
            {
                'choices': choices,
                'queries': _legacy_choice_queries(
                    slug, targets, request.query_params
                ),
                'target': target,
                'execution': execution,
                'color': color,
            }
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
        series = _published_series(slug, media=False)
        return Response(
            offers_service.variant_response(
                series,
                _series_variants(series),
                request.query_params,
                all_limit=ALL_ROWS_MAX,
            )
        )


class VariantDetailView(PublicReadMixin, APIView):
    def get(self, request, article):
        slug = request.query_params.get('series', '')
        series = _published_series(slug, media=False)
        found = _series_variants(series).filter(article=article)
        return Response(
            offers_service.detail_response(series, found, request.query_params)
        )
