import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.utils import FileSizeValidator
from apps.leads.models import Lead
from apps.leads.serializers import PHONE_MESSAGE

URL = '/api/leads/'


def form(**fields):
    return {
        'name': 'Анна',
        'phone': '+375 (29) 123-45-67',
        'contact_method': 'viber',
        'source': 'product/guardo-retta-6p',
        'page': '/catalog/radiatory/guardo-retta-6p',
        'context': 'Guardo Retta 6P; 1800 × 300; чёрный',
        'consent': 'on',
        'consent_version': '2026-11-04',
        **fields,
    }


def pdf(name='план.pdf', body=b'%PDF-1.7\n...'):
    return SimpleUploadedFile(name, body, content_type='application/pdf')


@pytest.fixture
def notify(monkeypatch):
    queued = []
    monkeypatch.setattr(
        'apps.leads.views.notify_lead.delay', lambda pk: queued.append(pk)
    )
    return queued


@pytest.mark.django_db
def test_lead_saved_with_consent(client, notify):  # noqa: ARG001
    response = client.post(URL, form(), REMOTE_ADDR='203.0.113.7')

    assert response.status_code == 201
    lead = Lead.objects.get()
    assert lead.phone == '+375291234567'
    assert lead.contact_method == 'viber'
    assert lead.consent_ip == '203.0.113.7'
    assert lead.consent_version == '2026-11-04'
    assert lead.consent_at is not None


@pytest.mark.django_db
def test_notification_queued_after_commit(
    client, notify, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        client.post(URL, form())

    assert notify == [Lead.objects.get().pk]


@pytest.mark.django_db
@pytest.mark.parametrize('phone', ['+7 999 123-45-67', '+375 29 123', ''])
def test_bad_phone_rejected(client, notify, phone):  # noqa: ARG001
    response = client.post(URL, form(phone=phone))

    assert response.status_code == 400
    assert 'phone' in response.json()
    assert not Lead.objects.exists()


@pytest.mark.django_db
def test_consent_required(client, notify):  # noqa: ARG001
    data = form()
    del data['consent']

    response = client.post(URL, data)

    assert response.status_code == 400
    assert 'consent' in response.json()


@pytest.mark.django_db
def test_honeypot_answers_ok_without_saving(client, notify):
    response = client.post(URL, form(website='http://spam.example'))

    assert response.status_code == 201
    assert not Lead.objects.exists()
    assert notify == []


@pytest.mark.django_db
def test_file_saved_privately_under_uuid(client, notify, private_storage):  # noqa: ARG001
    response = client.post(URL, form(file=pdf()))

    assert response.status_code == 201
    lead = Lead.objects.get()
    assert lead.file_name == 'план.pdf'
    assert lead.file.name.startswith('leads_lead/file/')
    assert lead.file.name.endswith('.pdf')
    assert 'план' not in lead.file.name
    assert private_storage.exists(lead.file.name)


@pytest.mark.django_db
@pytest.mark.parametrize(
    'upload',
    [
        pdf(body=b'MZ\x90\x00 not a pdf'),
        pdf(name='setup.exe', body=b'MZ\x90\x00'),
    ],
    ids=['wrong-signature', 'exe'],
)
def test_bad_file_rejected(client, notify, upload):  # noqa: ARG001
    response = client.post(URL, form(file=upload))

    assert response.status_code == 400
    assert 'file' in response.json()


@pytest.mark.django_db
def test_big_file_rejected(client, notify, monkeypatch):  # noqa: ARG001
    field = Lead._meta.get_field('file')  # noqa: SLF001
    size_validator = next(
        v for v in field.validators if isinstance(v, FileSizeValidator)
    )
    monkeypatch.setattr(size_validator, 'max_size_bytes', 10)

    response = client.post(URL, form(file=pdf(body=b'%PDF' + b'0' * 20)))

    assert response.status_code == 400
    assert 'file' in response.json()


@pytest.mark.django_db
def test_burst_throttled(client, notify):  # noqa: ARG001
    codes = [client.post(URL, form()).status_code for _ in range(4)]

    assert codes == [201, 201, 201, 429]


@pytest.mark.django_db
def test_regional_landline_accepted(client, notify):  # noqa: ARG001
    # Городской Гродно: регулярка на фронте раньше такой отсекала
    response = client.post(URL, form(phone='+375 152 12-34-56'))

    assert response.status_code == 201
    assert Lead.objects.get().phone == '+375152123456'


@pytest.mark.django_db
@pytest.mark.parametrize('phone', ['+7 999 123-45-67', '+375 29 123'])
def test_phone_error_message(client, notify, phone):  # noqa: ARG001
    response = client.post(URL, form(phone=phone))

    assert response.json()['phone'] == [PHONE_MESSAGE]
