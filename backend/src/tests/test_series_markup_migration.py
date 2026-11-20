from decimal import Decimal

import pytest
from django.core.exceptions import FieldDoesNotExist
from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_brand_markups_move_to_each_series_without_price_changes():
    executor = MigrationExecutor(connection)
    previous = [('catalog', '0014_image_alt_optional')]
    target = [('catalog', '0015_series_markup')]
    latest = executor.loader.graph.leaf_nodes()
    executor.migrate(previous)
    try:
        apps = executor.loader.project_state(previous).apps
        brand_model = apps.get_model('catalog', 'Brand')
        series_model = apps.get_model('catalog', 'Series')
        category = apps.get_model('catalog', 'Category').objects.create(
            name='Радиаторы', slug='migration-radiators'
        )
        brand = brand_model.objects.create(
            name='КЗТО', slug='migration-kzto', markup_percent=Decimal('12.50')
        )
        for slug in ('migration-quadrum', 'migration-neo'):
            series_model.objects.create(
                brand=brand, category=category, name=slug, slug=slug
            )
        first = series_model.objects.get(slug='migration-quadrum')
        apps.get_model('catalog', 'Variant').objects.create(
            brand_id=brand.pk,
            series_id=first.pk,
            article='migration-price',
            price=Decimal('100'),
            price_byn=Decimal('112.50'),
        )
        executor = MigrationExecutor(connection)
        executor.migrate(target)
        apps = executor.loader.project_state(target).apps
        migrated = apps.get_model('catalog', 'Series').objects.filter(
            brand_id=brand.pk
        )
        assert list(migrated.values_list('markup_percent', flat=True)) == [
            Decimal('12.50'),
            Decimal('12.50'),
        ]
        assert apps.get_model('catalog', 'Variant').objects.get(
            article='migration-price'
        ).price_byn == Decimal('112.50')
        model = apps.get_model('catalog', 'Brand')
        with pytest.raises(FieldDoesNotExist):
            model._meta.get_field('markup_percent')  # noqa: SLF001

        # Пока проценты одинаковые, обычный откат восстанавливает бренд.
        MigrationExecutor(connection).migrate(previous)
        old_apps = executor.loader.project_state(previous).apps
        assert old_apps.get_model('catalog', 'Brand').objects.get(
            pk=brand.pk
        ).markup_percent == Decimal('12.50')
        MigrationExecutor(connection).migrate(target)

        # Разные проценты нельзя молча свести к одному при откате.
        migrated.filter(slug='migration-quadrum').update(
            markup_percent=Decimal('15')
        )
        with pytest.raises(IrreversibleError):
            MigrationExecutor(connection).migrate(previous)
        assert migrated.get(
            slug='migration-quadrum'
        ).markup_percent == Decimal('15')
    finally:
        MigrationExecutor(connection).migrate(latest)
