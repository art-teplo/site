"""Подтверждённая возможность запроса окраски радиаторов в RAL."""

from .models import ColorGroup

ANY_RAL_BRANDS = ('kzto', 'radimax')


def supports_any_ral(series):
    return (
        series.category.slug == 'radiatory'
        and series.brand.slug in ANY_RAL_BRANDS
    )


def ensure_any_ral(series):
    if (
        not supports_any_ral(series)
        or series.color_groups.filter(any_ral=True).exists()
    ):
        return False
    # Группа только «по запросу» не должна заменить известную базовую цену.
    if not series.color_groups.exists():
        ColorGroup.objects.create(
            series=series, name='Базовый цвет', is_base=True, position=0
        )
    ColorGroup.objects.create(
        series=series, name='Любой RAL', any_ral=True, position=100
    )
    return True
