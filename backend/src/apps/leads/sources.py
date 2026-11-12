"""Источники заявок: значения `source` из LeadForm на фронте и их подписи.

Общие для админки и сообщения в Telegram.
"""

# Страница серии: series/<slug>. product/<slug> — так писали до каталога
# по сериям, остаётся для старых заявок
PRODUCT_PREFIXES = ('series/', 'product/')
PRODUCT_LABEL = 'Карточка товара'

# Источники с хвостом-слагом: catalog/<категория>, blog:<статья>
PREFIX_LABELS = {
    'catalog/': 'Каталог',
    'blog:': 'Статья блога',
}

LABELS = {
    'quiz': 'Квиз',
    'home': 'Главная',
    'home:paths': 'Главная, «С чего начнём?»',
    'podbor': 'Подбор',
    'partneram': 'Анкета партнёра',
    'shourum': 'Шоурум',
    'uslugi': 'Услуги',
    'proekty': 'Проекты',
    'klientam': 'Клиентам',
    'kontakty': 'Контакты',
    'brendy': 'Бренды',
    'blog': 'Блог',
    'catalog': 'Каталог',
}


def is_product(source: str) -> bool:
    return source.startswith(PRODUCT_PREFIXES)


def source_label(source: str) -> str:
    # Неизвестный источник (новая форма на фронте) показываем как есть
    if is_product(source):
        return PRODUCT_LABEL
    for prefix, label in PREFIX_LABELS.items():
        if source.startswith(prefix):
            return label
    return LABELS.get(source, source)
