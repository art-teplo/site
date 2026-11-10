import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.core.groups import (
    MANAGER_GROUP,
    manager_codenames,
    sync_manager_group,
)

PASSWORD = 'длинный-пароль-менеджера'


def codenames(group):
    return {
        f'{p.content_type.app_label}.{p.codename}'
        for p in group.permissions.select_related('content_type')
    }


@pytest.fixture
def manager(django_user_model):
    user = django_user_model.objects.create_user(
        'manager',
        password=PASSWORD,
        is_staff=True,
    )
    user.groups.add(Group.objects.get(name=MANAGER_GROUP))
    return user


@pytest.fixture
def manager_client(client, manager):
    client.force_login(manager)
    return client


def login(client, password, ip='10.0.0.1'):
    return client.post(
        reverse('admin:login'),
        {'username': 'manager', 'password': password},
        REMOTE_ADDR=ip,
    )


@pytest.mark.django_db
def test_manager_group_created_by_migrate():
    group = Group.objects.get(name=MANAGER_GROUP)

    assert codenames(group) == manager_codenames()


@pytest.mark.django_db
def test_sync_resets_manual_changes():
    group = Group.objects.get(name=MANAGER_GROUP)
    group.permissions.add(Permission.objects.get(codename='add_user'))

    sync_manager_group()

    assert codenames(group) == manager_codenames()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        'admin:leads_lead_changelist',
        'admin:content_post_add',
        'admin:catalog_brand_add',
        'admin:content_sitesettings_change',
    ],
)
def test_manager_opens_leads_and_content(manager_client, url):
    assert manager_client.get(reverse(url)).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        'admin:auth_user_changelist',
        'admin:auth_group_changelist',
        'admin:django_celery_beat_periodictask_changelist',
        'admin:axes_accessattempt_changelist',
    ],
)
def test_manager_has_no_users_or_system(manager_client, url):
    assert manager_client.get(reverse(url)).status_code == 403


@pytest.mark.django_db
def test_manager_cannot_change_site_settings(manager_client):
    url = reverse('admin:content_sitesettings_change')

    assert manager_client.post(url, {}).status_code == 403


@pytest.mark.django_db
def test_manager_cannot_delete_lead(manager_client, make_lead):
    lead = make_lead()
    url = reverse('admin:leads_lead_delete', args=[lead.pk])

    assert manager_client.get(url).status_code == 403


@pytest.mark.django_db
def test_login_locked_after_five_failures(client, manager):  # noqa: ARG001
    for _ in range(4):
        assert login(client, 'не тот').status_code == 200

    assert login(client, 'не тот').status_code == 429
    # Верный пароль тоже не пускает, пока блок не снят
    assert login(client, PASSWORD).status_code == 429
    # С другого адреса тот же логин входит: менеджера не заблокировать
    # чужими попытками
    assert login(client, PASSWORD, ip='10.0.0.2').status_code == 302


@pytest.mark.django_db
def test_success_resets_failures(client, manager):  # noqa: ARG001
    for _ in range(4):
        login(client, 'не тот')
    assert login(client, PASSWORD).status_code == 302
    client.logout()

    for _ in range(4):
        assert login(client, 'не тот').status_code == 200


@pytest.mark.parametrize(
    ('password', 'ok'),
    [('Короткий1!', False), ('длинный-пароль-менеджера', True)],
)
def test_password_needs_twelve_chars(password, ok):
    if ok:
        validate_password(password)
    else:
        with pytest.raises(ValidationError):
            validate_password(password)
