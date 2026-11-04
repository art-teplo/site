"""Источники заявок: значения `source` из LeadForm на фронте и их подписи.

Общие для админки и сообщения в Telegram.
"""

PRODUCT_PREFIX = 'product/'
PRODUCT_LABEL = 'Карточка товара'

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
}


def is_product(source: str) -> bool:
    return source.startswith(PRODUCT_PREFIX)


def source_label(source: str) -> str:
    # Неизвестный источник (новая форма на фронте) показываем как есть
    if is_product(source):
        return PRODUCT_LABEL
    return LABELS.get(source, source)
