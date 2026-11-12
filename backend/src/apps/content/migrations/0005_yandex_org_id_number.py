from django.db import migrations, models

HELP_TEXT = (
    'Для виджета отзывов: число из адреса карточки, '
    'yandex.by/maps/org/…/141315425329/. Пусто — вместо виджета '
    'только ссылка на карту'
)


def keep_only_numbers(apps, schema_editor):  # noqa: ARG001
    """Строка → число: пустое или не число (вставили не то) — в NULL."""
    site_settings = apps.get_model('content', 'SiteSettings')
    for site in site_settings.objects.all():
        if not (site.yandex_org_id or '').isdigit():
            site.yandex_org_id = None
            site.save(update_fields=['yandex_org_id'])


def null_to_empty(apps, schema_editor):  # noqa: ARG001
    site_settings = apps.get_model('content', 'SiteSettings')
    site_settings.objects.filter(yandex_org_id=None).update(yandex_org_id='')


class Migration(migrations.Migration):
    dependencies = [
        ('content', '0004_promo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='yandex_org_id',
            field=models.CharField(
                blank=True,
                max_length=32,
                null=True,
                verbose_name='id организации в Яндекс.Картах',
            ),
        ),
        migrations.RunPython(keep_only_numbers, null_to_empty),
        migrations.AlterField(
            model_name='sitesettings',
            name='yandex_org_id',
            field=models.PositiveBigIntegerField(
                blank=True,
                help_text=HELP_TEXT,
                null=True,
                verbose_name='id организации в Яндекс.Картах',
            ),
        ),
    ]
