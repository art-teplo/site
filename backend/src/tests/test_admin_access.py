import io
from decimal import Decimal
from html.parser import HTMLParser
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.catalog.models import (
    Brand,
    Category,
    ColorGroup,
    Series,
    SeriesImage,
    Variant,
)
from apps.content.models import Tag
from apps.core.groups import (
    MANAGER_GROUP,
    manager_codenames,
    sync_manager_group,
)

PASSWORD = 'длинный-пароль-менеджера'


def test_admin_configuration_passes_django_system_checks():
    from django.core.checks import Tags, run_checks  # noqa: PLC0415

    assert run_checks(tags=[Tags.admin]) == []


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
        'admin:catalog_productfamily_changelist',
        'admin:catalog_connectionoption_changelist',
        'admin:catalog_color_changelist',
        'admin:catalog_currencyrate_changelist',
    ]:
        assert manager_client.get(reverse(name)).status_code == 200, name

    add = manager_client.get(reverse('admin:catalog_currencyrate_add'))

    assert add.status_code == 403


@pytest.mark.django_db
def test_manager_can_preview_connection_without_creating_variant(
    manager_client,
):
    from apps.catalog.models import ConnectionOption, CurrencyRate  # noqa: PLC0415

    brand = Brand.objects.create(slug='kzto', name='КЗТО')
    category = Category.objects.create(slug='radiatory', name='Радиаторы')
    series = Series.objects.create(
        slug='preview',
        name='Пример',
        brand=brand,
        category=category,
        offer_mode='configured',
    )
    Variant.objects.create(
        series=series,
        article='preview-5',
        tubes=2,
        sections=5,
        price=10000,
        currency='RUB',
    )
    option = ConnectionOption.objects.create(
        series=series,
        source_id='test',
        label='Нижнее',
        tubes=2,
        mount='wall',
        connection='bottom_center',
        surcharge_rub=6007,
        allowed_sections=[5],
        checked_on='2026-11-18',
    )
    CurrencyRate.objects.create(
        currency='RUB', rate=Decimal('0.04'), date='2026-11-18'
    )
    before = Variant.objects.count()
    response = manager_client.get(
        reverse('admin:catalog_connectionoption_preview', args=[option.pk]),
        {'article': 'preview-5'},
    )
    assert response.status_code == 200
    assert response.context_data['row']['price'] == 640
    assert Variant.objects.count() == before
    assert (
        manager_client.get(
            reverse('admin:catalog_connectionoption_add')
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_catalog_admin_series_change_page_opens(manager_client):
    brand = Brand.objects.create(name='Б', slug='b')
    category = Category.objects.create(name='К', slug='k')
    series = Series.objects.create(brand=brand, category=category, name='С')

    url = reverse('admin:catalog_series_change', args=[series.pk])

    assert manager_client.get(url).status_code == 200


@pytest.mark.django_db
def test_series_markup_change_recalculates_prices(
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
            reverse('admin:catalog_series_change', args=[series.pk]),
            {
                'name': 'С',
                'slug': series.slug,
                'brand': brand.pk,
                'category': category.pk,
                'heating': 'water',
                'markup_percent': '10',
                'is_published': 'on',
                'color_groups-TOTAL_FORMS': '0',
                'color_groups-INITIAL_FORMS': '0',
                'images-TOTAL_FORMS': '0',
                'images-INITIAL_FORMS': '0',
                'files-TOTAL_FORMS': '0',
                'files-INITIAL_FORMS': '0',
                'showcases-TOTAL_FORMS': '0',
                'showcases-INITIAL_FORMS': '0',
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


def test_sortable_inlines_submit_their_order():
    """Перетаскивание в Unfold пишет порядок в поле формы: без поля в fields
    строки двигаются на экране, а после «Сохранить» порядок прежний."""
    from django.contrib import admin  # noqa: PLC0415

    missing = [
        f'{model_admin.__class__.__name__}.{inline.__name__}'
        for model_admin in admin.site._registry.values()  # noqa: SLF001
        for inline in model_admin.inlines
        # чужие инлайны (django-celery-beat) — не из Unfold, порядка у них нет
        if getattr(inline, 'ordering_field', None)
        and inline.ordering_field not in (inline.fields or [])
    ]
    assert missing == []


class _FormFields(HTMLParser):
    """Поля формы со страницы админки: то, что браузер отправит."""

    def __init__(self):
        super().__init__()
        self.data, self._select, self._textarea = {}, None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        name = a.get('name')
        if tag == 'input' and name and a.get('type') not in {'submit', 'file'}:
            if a.get('type') in {'checkbox', 'radio'} and 'checked' not in a:
                return
            self.data[name] = a.get('value') or ''
        elif tag == 'select' and name:
            self._select = name
            if 'multiple' not in a:  # пустой множественный выбор не шлётся
                self.data.setdefault(name, '')
        elif tag == 'option' and self._select and 'selected' in a:
            self.data[self._select] = a.get('value') or ''
        elif tag == 'textarea' and name:
            self._textarea = name
            self.data[name] = ''

    def handle_endtag(self, tag):
        if tag == 'select':
            self._select = None
        elif tag == 'textarea':
            self._textarea = None

    def handle_data(self, data):
        if self._textarea:
            self.data[self._textarea] += data


@pytest.mark.django_db
def test_series_saves_from_stale_form_without_order(admin_client):
    """Форма, открытая до появления поля порядка (или без JS), сохраняется,
    порядок фото прежний; группа цветов без фото не роняет сохранение."""
    brand = Brand.objects.create(name='Б', slug='b')
    category = Category.objects.create(name='К', slug='k')
    series = Series.objects.create(brand=brand, category=category, name='С')
    ColorGroup.objects.create(series=series, name='Стандарт', position=0)
    for position, alt in enumerate(['первое', 'второе']):
        buffer = io.BytesIO()
        Image.new('RGB', (4, 3)).save(buffer, 'PNG')
        SeriesImage.objects.create(
            series=series,
            image=SimpleUploadedFile('c.png', buffer.getvalue()),
            image_alt=alt,
            position=position,
        )
    url = reverse('admin:catalog_series_change', args=[series.pk])
    parser = _FormFields()
    parser.feed(admin_client.get(url).content.decode())
    data = {
        k: v
        for k, v in parser.data.items()
        if '__prefix__' not in k and not k.endswith('-position')
    }
    data['color_groups-0-name'] = 'Стандартные'  # строка изменилась

    response = admin_client.post(url, data)

    assert response.status_code == 302
    assert [i.image_alt for i in series.images.all()] == ['первое', 'второе']
    assert series.color_groups.get().name == 'Стандартные'
