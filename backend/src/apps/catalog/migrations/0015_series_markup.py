from django.db import migrations, models
from django.db.migrations.exceptions import IrreversibleError


def copy_to_series(apps, schema_editor):
    alias = schema_editor.connection.alias
    brand_model = apps.get_model('catalog', 'Brand')
    series_model = apps.get_model('catalog', 'Series')
    for brand_id, markup in brand_model.objects.using(alias).values_list(
        'pk', 'markup_percent'
    ):
        series_model.objects.using(alias).filter(brand_id=brand_id).update(
            markup_percent=markup
        )


def copy_to_brands(apps, schema_editor):
    alias = schema_editor.connection.alias
    brand_model = apps.get_model('catalog', 'Brand')
    series_model = apps.get_model('catalog', 'Series')
    for brand in brand_model.objects.using(alias).all():
        values = list(
            series_model.objects.using(alias)
            .filter(brand_id=brand.pk)
            .order_by()
            .values_list('markup_percent', flat=True)
            .distinct()
        )
        if len(values) > 1:
            message = (
                'Нельзя вернуть наценку бренда: у его серий разные проценты. '
                'Сохраните данные и согласуйте наценки перед откатом.'
            )
            raise IrreversibleError(message)
        if values:
            brand_model.objects.using(alias).filter(pk=brand.pk).update(
                markup_percent=values[0]
            )


class Migration(migrations.Migration):
    dependencies = [('catalog', '0014_image_alt_optional')]

    operations = [
        migrations.AddField(
            model_name='series',
            name='markup_percent',
            field=models.DecimalField(
                'наценка, %',
                max_digits=5,
                decimal_places=2,
                default=0,
                help_text='Для всех вариантов этой серии, после перевода по курсу Нацбанка',
            ),
        ),
        migrations.RunPython(copy_to_series, copy_to_brands),
        migrations.RemoveField(model_name='brand', name='markup_percent'),
    ]
