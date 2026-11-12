from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.catalog.models import (
    Brand,
    Category,
    ColorGroup,
    Series,
    Variant,
)
from apps.content.models import Tag
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


@pytest.mark.django_db
def test_manager_sees_catalog_admin_pages(manager_client):
    for name in [
        'admin:catalog_series_changelist',
        'admin:catalog_series_add',
        'admin:catalog_variant_changelist',
        'admin:catalog_variant_add',
        'admin:catalog_color_changelist',
        'admin:catalog_currencyrate_changelist',
    ]:
        assert manager_client.get(reverse(name)).status_code == 200, name

    add = manager_client.get(reverse('admin:catalog_currencyrate_add'))

    assert add.status_code == 403


@pytest.mark.django_db
def test_catalog_admin_series_change_page_opens(manager_client):
    brand = Brand.objects.create(name='Б', slug='b')
    category = Category.objects.create(name='К', slug='k')
    series = Series.objects.create(brand=brand, category=category, name='С')

    url = reverse('admin:catalog_series_change', args=[series.pk])

    assert manager_client.get(url).status_code == 200


@pytest.mark.django_db
def test_brand_markup_change_recalculates_prices(
    manager_client,
    django_capture_on_commit_callbacks,
):
    brand = Brand.objects.create(name='Б', slug='b')
    category = Category.objects.create(name='К', slug='k')
    series = Series.objects.create(brand=brand, category=category, name='С')
    variant = Variant.objects.create(
        series=series,
        article='A1',
        price=Decimal('100'),
        price_byn=Decimal('100'),
    )

    with django_capture_on_commit_callbacks(execute=False):
        response = manager_client.post(
            reverse('admin:catalog_brand_change', args=[brand.pk]),
            {
                'name': 'Б',
                'slug': 'b',
                'country': '',
                'note': 'Примечание',
                'markup_percent': '10',
                'is_published': 'on',
            },
        )

    assert response.status_code == 302
    variant.refresh_from_db()
    assert variant.price_byn == Decimal('110.00')


@pytest.fixture
def variant(db):  # noqa: ARG001
    brand = Brand.objects.create(name='Б', slug='b')
    category = Category.objects.create(name='К', slug='k')
    series = Series.objects.create(brand=brand, category=category, name='С')
    return Variant.objects.create(
        series=series,
        article='A1',
        price=Decimal('100'),
    )


def variant_post(variant, **extra):
    return {
        'series': variant.series_id,
        'article': variant.article,
        'is_active': 'on',
        'price': '100',
        'currency': 'BYN',
        'connection': '',
        'orientation': '',
        'mount': '',
        'attrs': '{}',
        **extra,
    }


def test_catalog_admin_variant_rejects_foreign_color_group(
    manager_client,
    variant,
):
    other = Series.objects.create(
        brand=variant.series.brand,
        category=variant.series.category,
        name='Другая',
        slug='other',
    )
    group = ColorGroup.objects.create(series=other, name='Г', percent=0)

    response = manager_client.post(
        reverse('admin:catalog_variant_change', args=[variant.pk]),
        variant_post(variant, color_groups=[group.pk]),
    )

    assert response.status_code == 200
    assert not variant.color_groups.exists()


def test_catalog_admin_variant_save_recalculates_and_revalidates(
    manager_client,
    variant,
    django_capture_on_commit_callbacks,
):
    with (
        patch('apps.catalog.admin.revalidate_frontend') as task,
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = manager_client.post(
            reverse('admin:catalog_variant_change', args=[variant.pk]),
            variant_post(variant, price='200'),
        )

    assert response.status_code == 302
    variant.refresh_from_db()
    assert variant.price_byn == Decimal('200.00')
    task.delay.assert_called_once_with(Tag.CATALOG)


def test_catalog_admin_variant_delete_revalidates_once(
    manager_client,
    variant,
    django_capture_on_commit_callbacks,
):
    with (
        patch('apps.catalog.admin.revalidate_frontend') as task,
        django_capture_on_commit_callbacks(execute=True),
    ):
        response = manager_client.post(
            reverse('admin:catalog_variant_delete', args=[variant.pk]),
            {'post': 'yes'},
        )

    assert response.status_code == 302
    assert not Variant.objects.exists()
    task.delay.assert_called_once_with(Tag.CATALOG)


def test_catalog_admin_variant_bulk_delete_revalidates_once(
    manager_client,
    variant,
    django_capture_on_commit_callbacks,
):
    Variant.objects.create(series=variant.series, article='A2')

    with (
        patch('apps.catalog.admin.revalidate_frontend') as task,
        django_capture_on_commit_callbacks(execute=True),
    ):
        manager_client.post(
            reverse('admin:catalog_variant_changelist'),
            {
                'action': 'delete_selected',
                '_selected_action': list(
                    Variant.objects.values_list('pk', flat=True),
                ),
                'post': 'yes',
            },
        )

    assert not Variant.objects.exists()
    task.delay.assert_called_once_with(Tag.CATALOG)


@pytest.mark.django_db
def test_manager_can_trigger_rates_update(manager_client):
    url = reverse('admin:catalog_currencyrate_changelist')

    with patch('apps.catalog.admin.update_rates.delay') as delay:
        page = manager_client.get(url)
        response = manager_client.get(
            reverse('admin:catalog_currencyrate_update_now'),
        )

    assert page.status_code == 200
    assert response.status_code == 302
    assert response.url == url
    delay.assert_called_once_with()
