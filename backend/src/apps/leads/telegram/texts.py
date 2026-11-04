"""Все тексты бота заявок — здесь. Формат — HTML (parse_mode бота).

Значения подставляются через .format(); пользовательский ввод экранирует
service.py.
"""

# --- сообщение о заявке ---

MSG_LEAD_TITLE = '<b>Заявка № {pk}</b> · {source}'
MSG_LEAD_NAME = '<b>{name}</b>'
MSG_LEAD_CONTACT = 'Связь: {method}'
MSG_LEAD_COMPANY = 'Студия: {company}'
MSG_LEAD_CITY = 'Город: {city}'
MSG_LEAD_COMMENT = 'Комментарий: {comment}'
MSG_LEAD_FILE = 'Файл: {name}'
MSG_LEAD_PRODUCT = '<a href="{url}">Открыть товар на сайте</a>'
MSG_LEAD_ADMIN = '<a href="{url}">Открыть в админке</a>'
MSG_LEAD_TAKEN = '✅ Взял: {name}'
MSG_LEAD_TAKEN_AT = '✅ Взял: {name} · {time}'
MSG_LEAD_FREE = '⏳ Свободна'

MSG_LEAD_RELEASED = 'Заявка № {pk} снова свободна'

# Подписи источников — в ../sources.py: они общие с админкой

# --- кнопки ---

BTN_TAKE = 'Беру'
# Кнопки в группе одни на всех: по имени видно, чья заявка
BTN_RELEASE = 'Отказаться ({name})'

# --- ответы на нажатия (всплывают у нажавшего) ---

ANSWER_TAKEN = 'Заявка ваша'
ANSWER_RELEASED = 'Вы отказались от заявки'
ALERT_TAKEN_BY = 'Заявку уже взял {name}'
ALERT_RELEASE_ONLY = 'Отказаться может только {name}'
ALERT_ALREADY_FREE = 'Заявка и так свободна'
ALERT_DELETED = 'Заявка уже удалена'
ALERT_UNAVAILABLE = 'Недоступно'

# --- команды ---

MSG_PRIVATE = (
    'Это служебный бот АртТепло: он присылает заявки с сайта '
    'в рабочую группу менеджеров.'
)
MSG_CHAT_ID = (
    'id этого чата: <code>{chat_id}</code>\n'
    'Впишите его в BACKEND__TELEGRAM__CHAT_ID.'
)
