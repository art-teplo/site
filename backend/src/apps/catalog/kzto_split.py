"""Планируемый, транзакционный перенос H/V без смены артикулов и цен."""

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Count, Q

from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend

from .importers.kzto import TARGETS, FeedError, parse_feed, read_feed
from .importers.kzto_series import LEGACY_SERIES
from .models import ColorGroup, Series, Showcase, Variant


@dataclass
class SplitPlan:
    parents: list[int]
    moves: list[tuple[int, int, str]]
    fingerprint: list[tuple]


def _fingerprint(parents):
    return list(
        Variant.objects.filter(series_id__in=parents)
        .order_by('pk')
        .values_list(
            'pk',
            'series_id',
            'article',
            'orientation',
            'connection',
            'price',
            'price_byn',
        )
    )


def _check_group_names(parents):
    roots = Series.objects.filter(pk__in=parents).values_list(
        'slug', flat=True
    )
    targets = [slug for root in roots for slug in LEGACY_SERIES[root]]
    duplicate = (
        ColorGroup.objects.filter(
            Q(series_id__in=parents) | Q(series__slug__in=targets)
        )
        .values('series_id', 'name')
        .annotate(n=Count('pk'))
        .filter(n__gt=1)
        .order_by('series_id', 'name')
        .first()
    )
    if duplicate:
        message = f'Неоднозначные группы цветов: серия {duplicate["series_id"]}, {duplicate["name"]}'
        raise FeedError(message)


def plan_kzto_split(
    *, feed_source: str, legacy_slugs: list[str] | None = None
) -> SplitPlan:
    categories, offers = parse_feed(read_feed(feed_source))
    mapping, seen = {}, set()
    for offer in offers:
        target = TARGETS.get(categories.get(offer.category))
        if target is None:
            continue
        article = offer.model or offer.name
        if article in seen:
            article = offer.name
        seen.add(article)
        mapping[article[:100], target.orientation] = target.slug
    parents = list(
        Series.objects.filter(
            brand__slug='kzto', slug__in=legacy_slugs or LEGACY_SERIES
        ).values_list('pk', flat=True)
    )
    _check_group_names(parents)
    moves = []
    for variant in Variant.objects.filter(
        series_id__in=parents
    ).select_related('series'):
        slug = mapping.get((variant.article, variant.orientation))
        if (
            not variant.orientation
            or slug not in LEGACY_SERIES[variant.series.slug]
        ):
            message = f'Неоднозначное исполнение: {variant.article}, {variant.series.slug}'
            raise FeedError(message)
        target = Series.objects.filter(slug=slug).first()
        if target and (
            target.brand_id != variant.brand_id
            or target.variants.filter(
                article=variant.article, connection=variant.connection
            ).exists()
        ):
            message = f'Конфликт целевой серии: {slug}, {variant.article}'
            raise FeedError(message)
        moves.append((variant.pk, variant.series_id, slug))
    return SplitPlan(parents, moves, _fingerprint(parents))


def _clone_fields(obj, excluded):
    return {
        f.attname: getattr(obj, f.attname)
        for f in obj._meta.concrete_fields  # noqa: SLF001
        if not f.primary_key and f.name not in excluded
    }


def apply_kzto_split(plan: SplitPlan) -> dict:
    with muted_revalidation(), transaction.atomic():
        list(Series.objects.select_for_update().filter(pk__in=plan.parents))
        list(
            Variant.objects.select_for_update().filter(
                series_id__in=plan.parents
            )
        )
        if _fingerprint(plan.parents) != plan.fingerprint:
            message = 'Данные изменились после предварительной проверки; постройте план заново'
            raise FeedError(message)
        _check_group_names(plan.parents)
        changed = bool(plan.moves)
        destinations, groups = {}, {}
        for old in Series.objects.filter(pk__in=plan.parents):
            for slug in LEGACY_SERIES[old.slug]:
                target = next(t for t in TARGETS.values() if t.slug == slug)
                new, _created = Series.objects.get_or_create(
                    slug=slug,
                    defaults={
                        **_clone_fields(
                            old,
                            {
                                'slug',
                                'name',
                                'description',
                                'video',
                                'video_poster',
                            },
                        ),
                        'name': target.name,
                        'description': '',
                    },
                )
                changed = changed or _created
                if new.brand_id != old.brand_id:
                    message = f'Чужой бренд у {slug}'
                    raise FeedError(message)
                destinations[slug] = new
                for group in old.color_groups.all():
                    copied = new.color_groups.filter(name=group.name).first()
                    if copied is None:
                        copied = ColorGroup.objects.create(
                            series=new,
                            legacy_origin=group,
                            **_clone_fields(
                                group, {'series', 'legacy_origin'}
                            ),
                        )
                        copied.colors.set(group.colors.all())
                    if copied.legacy_origin_id is None:
                        copied.legacy_origin = group
                        copied.save(update_fields=['legacy_origin'])
                    groups[slug, group.pk] = copied.pk
            changed = changed or old.is_published
            old.is_published = False
            old.save(update_fields=['is_published'])
        for variant_id, old_id, slug in plan.moves:
            variant = Variant.objects.get(pk=variant_id, series_id=old_id)
            old_groups = list(
                variant.color_groups.values_list('pk', flat=True)
            )
            Variant.objects.filter(pk=variant_id).update(
                series=destinations[slug]
            )
            variant.color_groups.set([groups[slug, pk] for pk in old_groups])
            Showcase.objects.filter(
                series_id=old_id, variant_id=variant_id
            ).update(series=destinations[slug])
        if changed:
            transaction.on_commit(
                lambda: revalidate_frontend.delay(Tag.CATALOG)
            )
        return {
            'moved': len(plan.moves),
            'series': sorted(destinations),
            'archived': len(plan.parents),
        }
