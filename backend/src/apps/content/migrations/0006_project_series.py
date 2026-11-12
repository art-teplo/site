from django.db import migrations, models


def slugs_to_series(apps, schema_editor):  # noqa: ARG001
    """Старые slug товаров переезжают в серии, если такая серия уже есть."""
    Project = apps.get_model('content', 'Project')
    Series = apps.get_model('catalog', 'Series')
    by_slug = {s.slug: s for s in Series.objects.all()}
    for project in Project.objects.exclude(product_slugs=[]):
        found = [by_slug[x] for x in project.product_slugs if x in by_slug]
        project.series.set(found)


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0004_variant_key_connection'),
        ('content', '0005_yandex_org_id_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='series',
            field=models.ManyToManyField(
                blank=True,
                related_name='projects',
                to='catalog.series',
                verbose_name='серии',
            ),
        ),
        migrations.RunPython(slugs_to_series, migrations.RunPython.noop),
        migrations.RemoveField(model_name='project', name='product_slugs'),
    ]
