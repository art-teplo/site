import pytest
from django.core.files.base import ContentFile
from django.urls import reverse


@pytest.fixture
def lead_with_file(make_lead):
    lead = make_lead(file_name='Проект квартиры.pdf')
    lead.file.save('x.pdf', ContentFile(b'%PDF-1.7'))
    return lead


@pytest.mark.django_db
def test_changelist_opens(admin_client, make_lead):
    make_lead()

    response = admin_client.get(reverse('admin:leads_lead_changelist'))

    assert response.status_code == 200


@pytest.mark.django_db
def test_change_page_shows_labels_and_status(
    admin_client, make_lead, settings
):
    settings.SITE_URL = 'http://lvh.me:3000'
    product = make_lead(
        source='product/guardo-retta',
        page='/catalog/radiatory/guardo-retta',
        context='Guardo Retta, 6 секций',
        tg_message_id=5,
    )
    partner = make_lead(source='partneram', page='/partneram')

    html = admin_client.get(
        reverse('admin:leads_lead_change', args=[product.pk])
    ).content.decode()
    assert 'Карточка товара' in html
    url = 'http://lvh.me:3000/catalog/radiatory/guardo-retta'
    assert f'href="{url}" target="_blank" rel="noopener">{url}</a>' in html
    assert 'Guardo Retta, 6 секций' in html
    assert 'Отправлена в группу' in html
    assert 'Telegram: чат' not in html

    html = admin_client.get(
        reverse('admin:leads_lead_change', args=[partner.pk])
    ).content.decode()
    assert 'Анкета партнёра' in html
    assert 'Не отправлена' in html
    assert 'контекст' not in html.lower()


@pytest.mark.django_db
def test_file_download_requires_staff(client, admin_client, lead_with_file):
    url = reverse('admin:leads_lead_file', args=[lead_with_file.pk])

    assert client.get(url).status_code == 302

    response = admin_client.get(url)
    assert response.status_code == 200
    disposition = response['Content-Disposition']
    assert disposition.startswith('attachment')
    assert "filename*=utf-8''" in disposition


@pytest.mark.django_db
def test_delete_removes_file(lead_with_file, private_storage):
    name = lead_with_file.file.name

    lead_with_file.delete()

    assert not private_storage.exists(name)


@pytest.mark.django_db
def test_manual_assignment_syncs_message(
    admin_client, make_lead, monkeypatch, django_capture_on_commit_callbacks
):
    synced = []
    monkeypatch.setattr(
        'apps.leads.admin.sync_lead_message.delay', synced.append
    )
    lead = make_lead(tg_chat_id=-1, tg_message_id=5, assignee_tg_id=9)
    url = reverse('admin:leads_lead_change', args=[lead.pk])

    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.post(url, {'assignee_name': 'Вера'})

    assert response.status_code == 302
    lead.refresh_from_db()
    assert lead.assignee_name == 'Вера'
    assert lead.assignee_tg_id is None
    assert lead.assigned_at is not None
    assert synced == [lead.pk]
