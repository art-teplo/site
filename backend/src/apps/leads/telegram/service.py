"""Сообщение о заявке в группе: текст, кнопка, отправка и правка.

Общее для Celery (отправка) и бота (правка после нажатия кнопки).
"""

from collections.abc import AsyncGenerator
from enum import StrEnum
from html import escape

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    Message,
    ReplyParameters,
    User,
)
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from ..models import Lead
from . import texts

# Лимит сообщения — 4096 символов; длинное целиком видно в админке
COMMENT_LIMIT = 1500
CONTEXT_LIMIT = 800
NAME_LIMIT = 150
BUTTON_NAME_LIMIT = 24

NOT_MODIFIED = 'message is not modified'


class LeadAction(CallbackData, prefix='lead'):
    class Action(StrEnum):
        TAKE = 'take'
        RELEASE = 'release'

    action: Action
    lead_id: int


class StorageInputFile(InputFile):
    """Файл из хранилища Django кусками: годится и для диска, и для S3."""

    def __init__(
        self,
        field_file,
        filename: str,
    ):
        super().__init__(filename=filename)
        self.field_file = field_file

    async def read(self, bot: Bot) -> AsyncGenerator[bytes]:  # noqa: ARG002
        with self.field_file.open('rb') as file:
            while chunk := file.read(self.chunk_size):
                yield chunk


def create_bot() -> Bot | None:
    """Бот из настроек или None, если токен не задан."""
    if not settings.TELEGRAM__BOT_TOKEN:
        return None
    return Bot(
        token=settings.TELEGRAM__BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
        ),
    )


def cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + '…'


def admin_url(lead: Lead) -> str:
    if not settings.PUBLIC_URL:
        return ''
    path = reverse('admin:leads_lead_change', args=[lead.pk])
    return f'{settings.PUBLIC_URL}{path}'


def display_name(user: User) -> str:
    """«Иван Петров (@ivan)» — так ответственный виден в группе и админке."""
    name = user.full_name
    if user.username:
        name = f'{name} (@{user.username})' if name else f'@{user.username}'
    return cut(name, NAME_LIMIT) or str(user.id)


def short_name(assignee_name: str) -> str:
    # «Иван Петров (@ivan)» → «Иван Петров»: на кнопке без ника
    return cut(assignee_name.split(' (@', maxsplit=1)[0], BUTTON_NAME_LIMIT)


def render_lead(lead: Lead) -> str:
    lines = [
        texts.MSG_LEAD_TITLE.format(
            pk=lead.pk,
            source=escape(lead.source_label),
        ),
        '',
        texts.MSG_LEAD_NAME.format(name=escape(lead.name)),
        lead.phone.as_international,
        texts.MSG_LEAD_CONTACT.format(
            method=lead.get_contact_method_display(),
        ),
    ]
    if lead.company:
        lines.append(
            texts.MSG_LEAD_COMPANY.format(company=escape(lead.company))
        )
    if lead.city:
        lines.append(texts.MSG_LEAD_CITY.format(city=escape(lead.city)))
    if lead.comment:
        comment = escape(cut(lead.comment, COMMENT_LIMIT))
        lines += ['', texts.MSG_LEAD_COMMENT.format(comment=comment)]
    if lead.context:
        lines += ['', escape(cut(lead.context, CONTEXT_LIMIT))]
    if lead.file_name:
        lines += ['', texts.MSG_LEAD_FILE.format(name=escape(lead.file_name))]
    # Страницу не показываем: её почти всегда повторяет источник.
    # Исключение — товар: ссылка на карточку
    links = []
    if lead.is_product and lead.page_url:
        links.append(texts.MSG_LEAD_PRODUCT.format(url=escape(lead.page_url)))
    url = admin_url(lead)
    if url:
        links.append(texts.MSG_LEAD_ADMIN.format(url=escape(url)))
    if links:
        lines += ['', *links]

    lines.append('')
    lines.append(render_status(lead))
    return '\n'.join(lines)


def render_status(lead: Lead) -> str:
    if not lead.assignee_name:
        return texts.MSG_LEAD_FREE
    name = escape(lead.assignee_name)
    if not lead.assigned_at:
        return texts.MSG_LEAD_TAKEN.format(name=name)
    time = f'{timezone.localtime(lead.assigned_at):%d.%m %H:%M}'
    return texts.MSG_LEAD_TAKEN_AT.format(
        name=name,
        time=time,
    )


def lead_keyboard(lead: Lead) -> InlineKeyboardMarkup:
    if lead.assignee_name:
        text = texts.BTN_RELEASE.format(name=short_name(lead.assignee_name))
        action = LeadAction.Action.RELEASE
    else:
        text, action = texts.BTN_TAKE, LeadAction.Action.TAKE
    button = InlineKeyboardButton(
        text=text,
        callback_data=LeadAction(
            action=action,
            lead_id=lead.pk,
        ).pack(),
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


async def send_lead(bot: Bot, lead: Lead, chat_id: int) -> Message:
    return await bot.send_message(
        chat_id=chat_id,
        text=render_lead(lead),
        reply_markup=lead_keyboard(lead),
    )


async def send_lead_file(bot: Bot, lead: Lead) -> None:
    """Файл заявки ответом на её сообщение."""
    await bot.send_document(
        chat_id=lead.tg_chat_id,
        document=StorageInputFile(
            lead.file,
            filename=lead.file_name or lead.file.name.rsplit('/', 1)[-1],
        ),
        reply_parameters=ReplyParameters(message_id=lead.tg_message_id),
        request_timeout=120,
    )


async def edit_lead(bot: Bot, lead: Lead) -> None:
    """Перерисовать текст и кнопку по текущему состоянию заявки."""
    try:
        await bot.edit_message_text(
            chat_id=lead.tg_chat_id,
            message_id=lead.tg_message_id,
            text=render_lead(lead),
            reply_markup=lead_keyboard(lead),
        )
    except TelegramBadRequest as error:
        # Текст не изменился (двойной клик, повтор задачи) — это не ошибка
        if NOT_MODIFIED not in error.message:
            raise


async def post_released(bot: Bot, lead: Lead) -> None:
    # Правка сообщения уведомления не даёт — пишем ответом
    await bot.send_message(
        chat_id=lead.tg_chat_id,
        text=texts.MSG_LEAD_RELEASED.format(pk=lead.pk),
        reply_parameters=ReplyParameters(message_id=lead.tg_message_id),
    )
