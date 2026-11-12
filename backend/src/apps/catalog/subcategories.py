"""Типы товаров по умолчанию: (slug, название) по slug категории."""

DEFAULT_TYPES: dict[str, list[tuple[str, str]]] = {
    'radiatory': [
        ('trubchatye', 'Трубчатые'),
        ('dizajn', 'Дизайн-радиаторы'),
        ('chugunnye', 'Чугунные'),
        ('alyuminievye', 'Алюминиевые'),
    ],
    'konvektory': [
        ('vnutripolnye', 'Внутрипольные'),
        ('napolnye', 'Напольные'),
        ('nastennye', 'Настенные'),
    ],
    'armatura': [
        ('ventili', 'Вентили'),
        ('avtomatika', 'Автоматика'),
    ],
}

# Тип существующих серий по slug; остальные серии радиаторов — трубчатые
SERIES_TYPES = {
    'guardo-allumo-3p': 'alyuminievye',
    'guardo-allumo-4p': 'alyuminievye',
}
DEFAULT_RADIATOR_TYPE = 'trubchatye'


def seed(subcategory_model, series_model, category_model):
    """Заводит типы для существующих категорий и проставляет серии без
    типа. Повторный вызов ничего не дублирует."""
    categories = {c.slug: c for c in category_model.objects.all()}
    for category_slug, items in DEFAULT_TYPES.items():
        category = categories.get(category_slug)
        if category is None:
            continue
        for position, (slug, name) in enumerate(items, start=1):
            subcategory_model.objects.get_or_create(
                slug=slug,
                defaults={
                    'category': category,
                    'name': name,
                    'position': position,
                },
            )
    radiators = categories.get('radiatory')
    if radiators is None:
        return
    for series in series_model.objects.filter(
        category=radiators,
        subcategory__isnull=True,
    ):
        slug = SERIES_TYPES.get(series.slug, DEFAULT_RADIATOR_TYPE)
        series.subcategory = subcategory_model.objects.filter(
            slug=slug,
        ).first()
        series.save(update_fields=['subcategory'])
