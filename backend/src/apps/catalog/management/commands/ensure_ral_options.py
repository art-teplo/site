import json

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.finishes import (
    ANY_RAL_BRANDS,
    ensure_any_ral,
    supports_any_ral,
)
from apps.catalog.models import Series
from apps.content.models import Tag
from apps.content.signals import muted_revalidation
from apps.content.tasks import revalidate_frontend


class Command(BaseCommand):
    help = 'Добавить «Любой RAL — по запросу» подтверждённым сериям радиаторов. Без --apply только отчёт.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--brand', choices=ANY_RAL_BRANDS, default='kzto')

    def handle(self, *args, **options):  # noqa: ARG002
        changed, excluded = [], []
        with muted_revalidation(), transaction.atomic():
            for series in Series.objects.filter(
                is_published=True,
                category__slug='radiatory',
                brand__slug=options['brand'],
            ).select_related('brand', 'category'):
                if not supports_any_ral(series):
                    excluded.append(series.slug)
                elif ensure_any_ral(series):
                    changed.append(series.slug)
            if not options['apply']:
                transaction.set_rollback(True)
            elif changed:
                transaction.on_commit(
                    lambda: revalidate_frontend.delay(Tag.CATALOG)
                )
        self.stdout.write(
            json.dumps(
                {
                    'added': changed,
                    'excluded': excluded,
                    'applied': options['apply'],
                },
                ensure_ascii=False,
            )
        )
