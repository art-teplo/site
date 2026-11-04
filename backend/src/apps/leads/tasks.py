import logging
from datetime import timedelta

from aiogram.exceptions import (
    TelegramAPIError,
    TelegramMigrateToChat,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from asgiref.sync import async_to_sync
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Lead
from .telegram.service import (
    create_bot,
    edit_lead,
    send_lead,
    send_lead_file,
)

logger = logging.getLogger(__name__)

# Сеть и 5xx у Telegram — повторяем с нарастающей паузой
TRANSIENT_ERRORS = (
    TelegramNetworkError,
    TelegramServerError,
)
RETRY = {
    'autoretry_for': TRANSIENT_ERRORS,
    'retry_backoff': True,
    'retry_backoff_max': 600,
    'max_retries': 10,
}


def handle_telegram_error(task, error, lead_id):
    if isinstance(error, TRANSIENT_ERRORS):
        raise error
    if isinstance(error, TelegramRetryAfter):
        raise task.retry(
            exc=error,
            countdown=error.retry_after,
        )
    if isinstance(error, TelegramMigrateToChat):
        logger.error(
            'Telegram: группа стала супергруппой, новый id %s — впишите его '
            'в BACKEND__TELEGRAM__CHAT_ID. Заявка %s не отправлена',
            error.migrate_to_chat_id,
            lead_id,
        )
        return
    # 400/403: наша ошибка или бота убрали из группы — повтор не поможет
    logger.error('Telegram: заявка %s не отправлена: %s', lead_id, error)


async def deliver(lead: Lead, chat_id: int) -> None:
    """Сообщение, потом файл ответом. Каждый шаг отмечается в заявке,
    так что повтор задачи не шлёт дубли."""
    async with create_bot().context() as bot:
        if not lead.tg_message_id:
            message = await send_lead(bot, lead, chat_id)
            lead.tg_chat_id = chat_id
            lead.tg_message_id = message.message_id
            await lead.asave(
                update_fields=[
                    'tg_chat_id',
                    'tg_message_id',
                ],
            )
        if lead.file and not lead.tg_file_sent:
            await send_lead_file(bot, lead)
            lead.tg_file_sent = True
            await lead.asave(update_fields=['tg_file_sent'])


async def redraw(lead: Lead) -> None:
    async with create_bot().context() as bot:
        await edit_lead(bot, lead)


@shared_task(bind=True, **RETRY)
def notify_lead(self, lead_id):
    """Заявка — в группу менеджеров."""
    chat_id = settings.TELEGRAM__CHAT_ID
    if not settings.TELEGRAM__BOT_TOKEN or not chat_id:
        logger.warning(
            'Telegram не настроен: заявка %s без уведомления',
            lead_id,
        )
        return
    lead = Lead.objects.filter(pk=lead_id).first()
    if lead is None:
        return
    try:
        async_to_sync(deliver)(lead, chat_id)
    except TelegramAPIError as error:
        handle_telegram_error(self, error, lead_id)


@shared_task(bind=True, **RETRY)
def sync_lead_message(self, lead_id):
    """Перерисовать сообщение в группе после правки заявки в админке."""
    lead = Lead.objects.filter(pk=lead_id).first()
    if not settings.TELEGRAM__BOT_TOKEN or lead is None:
        return
    if not lead.tg_message_id:
        return
    try:
        async_to_sync(redraw)(lead)
    except TelegramAPIError as error:
        handle_telegram_error(self, error, lead_id)


@shared_task
def purge_old_leads():
    """Удалить заявки и файлы старше срока хранения (раз в сутки, beat)."""
    cutoff = timezone.now() - timedelta(days=settings.LEADS__RETENTION_DAYS)
    deleted = 0
    # По одной: post_delete удаляет файл каждой заявки
    for lead in Lead.objects.filter(created_at__lt=cutoff).iterator():
        lead.delete()
        deleted += 1
    if deleted:
        logger.info('Удалено старых заявок: %s', deleted)
    return deleted
