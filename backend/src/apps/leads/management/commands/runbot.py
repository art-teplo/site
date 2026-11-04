import asyncio
import logging
import time

from django.core.management.base import BaseCommand

from apps.leads.telegram.handlers import get_dispatcher
from apps.leads.telegram.service import create_bot

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Бот заявок: принимает нажатия кнопок (long polling)'

    def handle(self, *args, **options):  # noqa: ARG002
        bot = create_bot()
        if bot is None:
            # Без токена не падаем: иначе compose перезапускает сервис по кругу
            logger.warning('BACKEND__TELEGRAM__BOT_TOKEN не задан, бот спит')
            while True:
                time.sleep(3600)

        dispatcher = get_dispatcher()
        # Повторы при сетевых ошибках и SIGTERM обрабатывает сам aiogram
        asyncio.run(
            dispatcher.start_polling(
                bot,
                allowed_updates=dispatcher.resolve_used_update_types(),
            ),
        )
