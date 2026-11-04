"""Кнопки «Беру» / «Отказаться» и служебные команды бота заявок.

От способа получения обновлений не зависит: сейчас их приносит long
polling (команда runbot), при переходе на вебхук — Dispatcher.feed_update.
"""

import logging
from functools import cache

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import (
    JOIN_TRANSITION,
    ChatMemberUpdatedFilter,
    Command,
    Filter,
)
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from ..models import Lead
from . import texts
from .service import LeadAction, display_name, edit_lead, post_released

logger = logging.getLogger(__name__)

router = Router(name='leads')


class WorkChat(Filter):
    """Нажатие пришло из группы заявок (BACKEND__TELEGRAM__CHAT_ID)."""

    async def __call__(self, query: CallbackQuery) -> bool:
        chat_id = settings.TELEGRAM__CHAT_ID
        return bool(chat_id) and query.message.chat.id == chat_id


async def refresh(bot: Bot, lead: Lead) -> None:
    try:
        await edit_lead(bot, lead)
    except TelegramAPIError:
        # Ответственный уже записан в базе; сообщение догонит правка в админке
        logger.exception('Telegram: не удалось обновить заявку %s', lead.pk)


@router.callback_query(
    LeadAction.filter(F.action == LeadAction.Action.TAKE),
    WorkChat(),
)
async def take_lead(
    query: CallbackQuery,
    callback_data: LeadAction,
    bot: Bot,
) -> None:
    lead_id = callback_data.lead_id
    # Условный UPDATE: из двух одновременных нажатий выигрывает одно
    taken = await Lead.objects.filter(
        pk=lead_id,
        assignee_tg_id__isnull=True,
        assignee_name='',
    ).aupdate(
        assignee_tg_id=query.from_user.id,
        assignee_name=display_name(query.from_user),
        assigned_at=timezone.now(),
    )
    lead = await Lead.objects.filter(pk=lead_id).afirst()
    if lead is None:
        await query.answer(texts.ALERT_DELETED, show_alert=True)
        return
    if not taken:
        await query.answer(
            texts.ALERT_TAKEN_BY.format(name=lead.assignee_name),
            show_alert=True,
        )
        return
    await refresh(bot, lead)
    await query.answer(texts.ANSWER_TAKEN)


@router.callback_query(
    LeadAction.filter(F.action == LeadAction.Action.RELEASE),
    WorkChat(),
)
async def release_lead(
    query: CallbackQuery,
    callback_data: LeadAction,
    bot: Bot,
) -> None:
    lead_id = callback_data.lead_id
    # Отказаться может тот, кто взял; если ответственного назначили
    # в админке (без id в Telegram) — любой из группы
    released = (
        await Lead.objects.filter(pk=lead_id)
        .filter(
            Q(assignee_tg_id=query.from_user.id)
            | Q(assignee_tg_id__isnull=True),
        )
        .exclude(assignee_name='')
        .aupdate(
            assignee_tg_id=None,
            assignee_name='',
            assigned_at=None,
        )
    )
    lead = await Lead.objects.filter(pk=lead_id).afirst()
    if lead is None:
        await query.answer(texts.ALERT_DELETED, show_alert=True)
        return
    if not released:
        if lead.assignee_name:
            text = texts.ALERT_RELEASE_ONLY.format(name=lead.assignee_name)
        else:
            text = texts.ALERT_ALREADY_FREE
        await query.answer(text, show_alert=True)
        return
    await refresh(bot, lead)
    await post_released(bot, lead)
    await query.answer(texts.ANSWER_RELEASED)


@router.callback_query()
async def unknown_callback(query: CallbackQuery) -> None:
    # Чужой чат или старая кнопка: снимаем «часики» у нажавшего
    await query.answer(texts.ALERT_UNAVAILABLE)


@router.message(F.chat.type == ChatType.PRIVATE)
async def private_message(message: Message) -> None:
    await message.answer(texts.MSG_PRIVATE)


@router.message(Command('chatid'))
async def chat_id_command(message: Message) -> None:
    await message.answer(texts.MSG_CHAT_ID.format(chat_id=message.chat.id))


@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION),
    F.chat.type != ChatType.PRIVATE,
)
async def bot_joined(event: ChatMemberUpdated, bot: Bot) -> None:
    logger.info(
        'Telegram: бота добавили в «%s», id=%s',
        event.chat.title,
        event.chat.id,
    )
    configured = settings.TELEGRAM__CHAT_ID
    if configured and event.chat.id != configured:
        # Заявки уходят только в одну группу: из чужих бот выходит сам
        await bot.leave_chat(chat_id=event.chat.id)


@cache
def get_dispatcher() -> Dispatcher:
    # Роутер подключается к диспетчеру один раз на процесс
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    return dispatcher
