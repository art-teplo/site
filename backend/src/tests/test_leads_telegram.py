from datetime import timedelta

import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramMigrateToChat,
    TelegramRetryAfter,
)
from aiogram.methods import (
    AnswerCallbackQuery,
    EditMessageText,
    LeaveChat,
    SendDocument,
    SendMessage,
)
from aiogram.types import Update, User
from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.leads.models import Lead
from apps.leads.tasks import notify_lead, purge_old_leads
from apps.leads.telegram import texts
from apps.leads.telegram.handlers import get_dispatcher
from apps.leads.telegram.service import (
    LeadAction,
    display_name,
    lead_keyboard,
    render_lead,
)
from tests.conftest import BOT_USER, CHAT_ID

IVAN = {
    'id': 1,
    'is_bot': False,
    'first_name': 'Иван',
    'username': 'ivan',
}
OLGA = {
    'id': 2,
    'is_bot': False,
    'first_name': 'Ольга',
}
TAKE = LeadAction.Action.TAKE
RELEASE = LeadAction.Action.RELEASE


def feed(tg, **update):
    """Прогнать обновление через диспетчер, как это делает polling."""
    event = Update.model_validate(
        {'update_id': 1, **update},
        context={'bot': tg.bot},
    )
    async_to_sync(get_dispatcher().feed_update)(tg.bot, event)


def press(tg, lead_id, user, action, chat_id=CHAT_ID):
    feed(
        tg,
        callback_query={
            'id': 'q1',
            'from': user,
            'chat_instance': 'ci',
            'data': LeadAction(action=action, lead_id=lead_id).pack(),
            'message': {
                'message_id': 55,
                'date': 0,
                'chat': {'id': chat_id, 'type': 'supergroup'},
            },
        },
    )


@pytest.fixture
def posted(make_lead):
    """Заявка, уже отправленная в группу."""

    def make(**fields):
        return make_lead(tg_chat_id=CHAT_ID, tg_message_id=55, **fields)

    return make


# --- текст ---


@pytest.mark.django_db
def test_render_escapes_html(make_lead):
    lead = make_lead(name='<b>Анна</b>', comment='a & b')

    text = render_lead(lead)

    assert '&lt;b&gt;Анна&lt;/b&gt;' in text
    assert 'a &amp; b' in text
    assert '+375 29 123-45-67' in text
    assert texts.MSG_LEAD_FREE in text


@pytest.mark.django_db
def test_render_links_product_not_page(make_lead, settings):
    settings.SITE_URL = 'https://art-teplo.by'
    settings.PUBLIC_URL = 'https://api.art-teplo.by'
    product = make_lead(
        source='product/guardo-retta',
        page='/catalog/radiatory/guardo-retta',
    )
    quiz = make_lead(source='quiz', page='/podbor')

    text = render_lead(product)
    assert 'Карточка товара' in text
    assert (
        '<a href="https://art-teplo.by/catalog/radiatory/guardo-retta">'
        in text
    )
    assert f'/admin/leads/lead/{product.pk}/change/' in text

    text = render_lead(quiz)
    assert '/podbor' not in text
    assert 'Открыть товар на сайте' not in text


@pytest.mark.django_db
def test_page_url_ignores_foreign_domain(make_lead, settings):
    settings.SITE_URL = 'https://art-teplo.by'

    assert make_lead(page='//evil.example/x').page_url == ''
    assert make_lead(page='https://evil.example').page_url == ''


def test_release_button_shows_short_name():
    lead = Lead(pk=1, assignee_name='Иван Петров (@ivan)')

    button = lead_keyboard(lead).inline_keyboard[0][0]

    assert button.text == 'Отказаться (Иван Петров)'


def test_display_name():
    assert display_name(User(**IVAN)) == 'Иван (@ivan)'
    assert display_name(User(**OLGA)) == 'Ольга'


# --- отправка ---


@pytest.mark.django_db
def test_notify_sends_message_then_file(tg, make_lead):
    lead = make_lead(file_name='план.pdf')
    lead.file.save('x.pdf', ContentFile(b'%PDF-1.7'))

    notify_lead.apply(args=[lead.pk])

    assert tg.methods() == ['SendMessage', 'SendDocument']
    message = tg.last(SendMessage)
    assert message.chat_id == CHAT_ID
    assert message.reply_markup.inline_keyboard[0][0].text == texts.BTN_TAKE
    lead.refresh_from_db()
    assert lead.tg_message_id == 101
    assert lead.tg_file_sent
    assert tg.last(SendDocument).reply_parameters.message_id == 101
    assert tg.documents == [('план.pdf', b'%PDF-1.7')]


@pytest.mark.django_db
def test_notify_does_not_repeat_sent_message(tg, posted):
    lead = posted(file_name='a.pdf')
    lead.file.save('x.pdf', ContentFile(b'%PDF-1.7'))

    notify_lead.apply(args=[lead.pk])

    assert tg.methods() == ['SendDocument']


@pytest.mark.django_db
def test_notify_skipped_without_token(tg, settings, make_lead):
    settings.TELEGRAM__BOT_TOKEN = ''

    notify_lead.apply(args=[make_lead().pk])

    assert tg.calls == []


@pytest.mark.django_db
def test_notify_permanent_error_not_retried(tg, make_lead):
    tg.errors[SendMessage] = lambda m: TelegramBadRequest(m, 'chat not found')
    lead = make_lead()

    result = notify_lead.apply(args=[lead.pk])

    assert result.successful()
    assert tg.methods() == ['SendMessage']
    lead.refresh_from_db()
    assert lead.tg_message_id is None


@pytest.mark.django_db
def test_notify_migrated_chat_not_retried(tg, make_lead):
    tg.errors[SendMessage] = lambda m: TelegramMigrateToChat(m, 'moved', -1)

    result = notify_lead.apply(args=[make_lead().pk])

    assert result.successful()
    assert tg.methods() == ['SendMessage']


@pytest.mark.django_db
def test_notify_retries_on_flood_limit(tg, make_lead):
    tg.errors[SendMessage] = lambda m: TelegramRetryAfter(m, 'Too Many', 5)

    result = notify_lead.apply(args=[make_lead().pk])

    # В eager-режиме Celery повторяет сразу: первая попытка + max_retries
    assert result.failed()
    assert tg.methods() == ['SendMessage'] * 11


# --- кнопки ---


@pytest.mark.django_db
def test_take_assigns_free_lead(tg, posted):
    lead = posted()

    press(tg, lead.pk, IVAN, TAKE)

    lead.refresh_from_db()
    assert lead.assignee_tg_id == 1
    assert lead.assignee_name == 'Иван (@ivan)'
    edit = tg.last(EditMessageText)
    assert 'Взял: Иван (@ivan)' in edit.text
    assert edit.reply_markup.inline_keyboard[0][0].text == 'Отказаться (Иван)'
    assert tg.last(AnswerCallbackQuery).text == texts.ANSWER_TAKEN


@pytest.mark.django_db
def test_take_refused_when_taken(tg, posted):
    lead = posted(
        assignee_tg_id=1,
        assignee_name='Иван (@ivan)',
    )

    press(tg, lead.pk, OLGA, TAKE)

    lead.refresh_from_db()
    assert lead.assignee_tg_id == 1
    answer = tg.last(AnswerCallbackQuery)
    assert answer.text == 'Заявку уже взял Иван (@ivan)'
    assert answer.show_alert is True
    assert 'EditMessageText' not in tg.methods()


@pytest.mark.django_db
def test_release_only_by_assignee(tg, posted):
    lead = posted(
        assignee_tg_id=1,
        assignee_name='Иван (@ivan)',
    )

    press(tg, lead.pk, OLGA, RELEASE)

    lead.refresh_from_db()
    assert lead.assignee_tg_id == 1
    answer = tg.last(AnswerCallbackQuery)
    assert answer.text == 'Отказаться может только Иван (@ivan)'


@pytest.mark.django_db
def test_release_frees_and_posts_notice(tg, posted):
    lead = posted(
        assignee_tg_id=1,
        assignee_name='Иван (@ivan)',
        assigned_at=timezone.now(),
    )

    press(tg, lead.pk, IVAN, RELEASE)

    lead.refresh_from_db()
    assert lead.assignee_name == ''
    assert lead.assignee_tg_id is None
    assert texts.MSG_LEAD_FREE in tg.last(EditMessageText).text
    notice = tg.last(SendMessage)
    assert notice.text == f'Заявка № {lead.pk} снова свободна'
    assert notice.reply_parameters.message_id == 55


@pytest.mark.django_db
def test_admin_assignment_released_by_anyone(tg, posted):
    lead = posted(assignee_name='Вера')

    press(tg, lead.pk, OLGA, RELEASE)

    lead.refresh_from_db()
    assert lead.assignee_name == ''


@pytest.mark.django_db
def test_press_from_other_chat_ignored(tg, posted):
    lead = posted()

    press(tg, lead.pk, IVAN, TAKE, chat_id=-999)

    lead.refresh_from_db()
    assert lead.assignee_name == ''
    assert tg.methods() == ['AnswerCallbackQuery']
    assert tg.last(AnswerCallbackQuery).text == texts.ALERT_UNAVAILABLE


@pytest.mark.django_db
def test_press_on_deleted_lead(tg, posted):
    lead = posted()
    lead_id = lead.pk
    lead.delete()

    press(tg, lead_id, IVAN, TAKE)

    assert tg.last(AnswerCallbackQuery).text == texts.ALERT_DELETED


@pytest.mark.django_db
def test_not_modified_is_not_an_error(tg, posted):
    tg.errors[EditMessageText] = lambda m: TelegramBadRequest(
        m,
        'Bad Request: message is not modified',
    )
    lead = posted()

    press(tg, lead.pk, IVAN, TAKE)

    assert tg.last(AnswerCallbackQuery).text == texts.ANSWER_TAKEN


# --- команды и чаты ---


def test_private_message_replies(tg):
    feed(
        tg,
        message={
            'message_id': 1,
            'date': 0,
            'text': '/start',
            'from': IVAN,
            'chat': {'id': 1, 'type': 'private'},
        },
    )

    assert tg.last(SendMessage).text == texts.MSG_PRIVATE


def test_chatid_in_group(tg):
    feed(
        tg,
        message={
            'message_id': 1,
            'date': 0,
            'text': '/chatid@artteplo_bot',
            'from': IVAN,
            'chat': {'id': -100555, 'type': 'supergroup'},
        },
    )

    assert '-100555' in tg.last(SendMessage).text


def test_leaves_foreign_group(tg):
    bot_member = BOT_USER.model_dump()
    feed(
        tg,
        my_chat_member={
            'chat': {'id': -100555, 'type': 'supergroup', 'title': 'Чужая'},
            'from': IVAN,
            'date': 0,
            'old_chat_member': {'status': 'left', 'user': bot_member},
            'new_chat_member': {'status': 'member', 'user': bot_member},
        },
    )

    assert tg.last(LeaveChat).chat_id == -100555


# --- хранение ---


@pytest.mark.django_db
def test_purge_removes_old_leads_and_files(make_lead, private_storage):
    old = make_lead()
    old.file.save('old.pdf', ContentFile(b'%PDF'))
    Lead.objects.filter(pk=old.pk).update(
        created_at=timezone.now() - timedelta(days=366),
    )
    fresh = make_lead()

    assert purge_old_leads() == 1

    assert list(Lead.objects.values_list('pk', flat=True)) == [fresh.pk]
    assert not private_storage.exists(old.file.name)
