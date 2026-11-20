"""Однократное проверяемое связывание групп уже перенесённых исполнений."""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.importers.factory_editions import legacy_targets
from apps.catalog.importers.kzto_series import LEGACY_SERIES
from apps.catalog.models import ColorGroup, Series
from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend


def _links():
    result = {'links': [], 'conflicts': []}
    for parent_slug, targets in {**LEGACY_SERIES, **legacy_targets()}.items():
        old = Series.objects.filter(slug=parent_slug).first()
        if old is None or old.variants.exists():
            continue
        for target in Series.objects.filter(slug__in=targets):
            if (
                target.brand_id != old.brand_id
                or target.category_id != old.category_id
            ):
                result['conflicts'].append(f'Бренд/категория: {target.slug}')
                continue
            for origin in old.color_groups.prefetch_related('colors'):
                if target.color_groups.filter(legacy_origin=origin).exists():
                    continue
                candidates = list(
                    target.color_groups.filter(
                        legacy_origin__isnull=True,
                        name=origin.name,
                        percent=origin.percent,
                        any_ral=origin.any_ral,
                        is_base=origin.is_base,
                    ).prefetch_related('colors')
                )
                candidates = [
                    g
                    for g in candidates
                    if {c.pk for c in g.colors.all()}
                    == {c.pk for c in origin.colors.all()}
                ]
                if len(candidates) != 1:
                    result['conflicts'].append(
                        f'Нет однозначного соответствия: {target.slug}, исходная группа {origin.pk}'
                    )
                    continue
                result['links'].append(
                    {
                        'group_id': candidates[0].pk,
                        'legacy_origin_id': origin.pk,
                        'series': target.slug,
                    }
                )
    return result


class Command(BaseCommand):
    help = 'Связать старые ID групп с уже перенесёнными исполнениями. Без --apply только отчёт.'

    def add_arguments(self, parser):
        parser.add_argument('--report', type=Path, required=True)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):  # noqa: ARG002
        with muted_revalidation(), transaction.atomic():
            if options['apply']:
                list(ColorGroup.objects.select_for_update().order_by('pk'))
            result = _links()
            options['report'].write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + '\n'
            )
            if options['apply'] and result['conflicts']:
                message = 'Связывание остановлено: ' + '; '.join(
                    result['conflicts'][:5]
                )
                raise CommandError(message)
            if options['apply']:
                for link in result['links']:
                    ColorGroup.objects.filter(pk=link['group_id']).update(
                        legacy_origin_id=link['legacy_origin_id']
                    )
                if result['links']:
                    transaction.on_commit(
                        lambda: revalidate_frontend.delay(Tag.CATALOG)
                    )
        self.stdout.write(
            json.dumps(
                {
                    'links': len(result['links']),
                    'conflicts': len(result['conflicts']),
                    'applied': options['apply'],
                },
                ensure_ascii=False,
            )
        )
