import pytest
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.methods import GetMe, SendDocument, SendMessage
from aiogram.types import Chat, Message, User
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.utils import timezone

from apps.leads.models import Lead


@pytest.fixture(autouse=True)
def _plain_static_storage(settings):
    # Manifest-хранилище требует collectstatic; в тестах статику не собираем
    settings.STORAGES = {
        **settings.STORAGES,
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }


@pytest.fixture(autouse=True)
def _clear_cache():
    # Счётчики троттлинга живут в кэше и иначе переходят из теста в тест
    cache.clear()


@pytest.fixture(autouse=True)
def private_storage(tmp_path, monkeypatch):
    # Хранилище поля создаётся при импорте модели — подменяем его самого
    storage = FileSystemStorage(location=tmp_path / 'private')
    field = Lead._meta.get_field('file')  # noqa: SLF001
    monkeypatch.setattr(field, 'storage', storage)
    return storage


class FakeSession(BaseSession):
    """Сессия aiogram без сети: записывает методы Bot API и отвечает
    настоящими типами. errors: тип метода → функция(method) → исключение."""

    def __init__(self):
        super().__init__()
        self.calls = []
        self.errors = {}
        self.documents = []

    async def make_request(self, bot, method, timeout=None):  # noqa: ARG002
        self.calls.append(method)
        if type(method) in self.errors:
            raise self.errors[type(method)](method)
        if isinstance(method, SendDocument):
            # Читаем файл так же, как настоящая сессия перед отправкой
            body = b''.join(
                [chunk async for chunk in method.document.read(bot)]
            )
            self.documents.append((method.document.filename, body))
        if isinstance(method, SendMessage | SendDocument):
            return Message(
                message_id=100 + len(self.calls),
                date=timezone.now(),
                chat=Chat(
                    id=method.chat_id,
                    type='supergroup',
                ),
            )
        if isinstance(method, GetMe):
            return BOT_USER
        return True

    async def stream_content(self, *args, **kwargs):  # noqa: ARG002
        raise NotImplementedError
        yield b''

    async def close(self):
        pass

    def methods(self):
        return [type(method).__name__ for method in self.calls]

    def last(self, method_type):
        return next(
            m for m in reversed(self.calls) if isinstance(m, method_type)
        )


CHAT_ID = -100123
BOT_USER = User(
    id=42,
    is_bot=True,
    first_name='Бот',
    username='artteplo_bot',
)


@pytest.fixture
def tg(settings, monkeypatch):
    """Telegram настроен, все запросы бота уходят в FakeSession."""
    settings.TELEGRAM__BOT_TOKEN = '42:TEST'
    settings.TELEGRAM__CHAT_ID = CHAT_ID
    session = FakeSession()

    def create_bot():
        return Bot(
            token=settings.TELEGRAM__BOT_TOKEN,
            session=session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    monkeypatch.setattr('apps.leads.tasks.create_bot', create_bot)
    session.bot = create_bot()
    return session


@pytest.fixture
def make_lead(db):  # noqa: ARG001
    def make(**fields):
        data = {
            'name': 'Анна',
            'phone': '+375291234567',
            'source': 'quiz',
            'consent_at': timezone.now(),
            'consent_version': '2026-11-04',
            **fields,
        }
        return Lead.objects.create(**data)

    return make
