from django.db import migrations

from apps.catalog.subcategories import seed


def seed_types(apps, schema_editor):  # noqa: ARG001
    seed(
        apps.get_model('catalog', 'Subcategory'),
        apps.get_model('catalog', 'Series'),
        apps.get_model('catalog', 'Category'),
    )


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0005_subcategories_image_kind'),
    ]

    operations = [
        migrations.RunPython(seed_types, migrations.RunPython.noop),
    ]
