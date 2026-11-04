from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.catalog.models import Brand, Category, LeadTime
from apps.content.models import Tag
from apps.content.tasks import revalidate_frontend
from tests.test_content import media, with_image  # noqa: F401

# --- API ---


@pytest.fixture
def brands(db):  # noqa: ARG001
    kzto = Brand.objects.create(
        slug='kzto',
        name='КЗТО',
        country='Россия',
        note='Официальный представитель',
        warranty_years=10,
        position=1,
    )
    hidden = Brand.objects.create(
        slug='hidden',
        name='Скрытый',
        note='—',
        is_published=False,
    )
    return kzto, hidden


@pytest.mark.django_db
def test_brands_published_in_order(client, brands):
    kzto, _ = brands
    Brand.objects.create(slug='guardo', name='Guardo', note='—', position=0)

    data = client.get(reverse('brand-list')).json()

    assert [brand['slug'] for brand in data] == ['guardo', 'kzto']
    assert data[1]['warranty_years'] == kzto.warranty_years
    assert data[1]['logo'] is None


@pytest.mark.django_db
def test_lead_times_hide_unpublished_brand(client, brands):
    kzto, hidden = brands
    LeadTime.objects.create(brand=kzto, series='Квадрум', days=15, position=1)
    LeadTime.objects.create(brand=kzto, series='Вертикальный', position=0)
    LeadTime.objects.create(brand=hidden, series='Секрет', days=5)

    data = client.get(reverse('lead-time-list')).json()

    assert [(row['series'], row['brand'], row['days']) for row in data] == [
        ('Вертикальный', 'kzto', None),
        ('Квадрум', 'kzto', 15),
    ]
    assert data[0]['updated_at']


@pytest.mark.django_db
def test_categories_with_image(client):
    with_image(
        Category(
            slug='radiatory',
            name='Радиаторы',
            short='Трубчатые',
            image_alt='Радиатор',
        ),
    )
    with_image(
        Category(
            slug='skryt',
            name='Скрытая',
            short='—',
            image_alt='—',
            is_published=False,
        ),
    )

    data = client.get(reverse('category-list')).json()

    assert [category['slug'] for category in data] == ['radiatory']
    assert data[0]['image']['alt'] == 'Радиатор'


@pytest.mark.django_db
def test_change_asks_frontend_to_revalidate_catalog(
    django_capture_on_commit_callbacks,
):
    with (
        patch.object(revalidate_frontend, 'delay') as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        Brand.objects.create(slug='nova', name='Nova', note='—')

    delay.assert_called_once_with(Tag.CATALOG)


# --- админка ---


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        'admin:catalog_category_changelist',
        'admin:catalog_category_add',
        'admin:catalog_brand_changelist',
        'admin:catalog_brand_add',
        'admin:catalog_leadtime_changelist',
        'admin:catalog_leadtime_add',
    ],
)
def test_admin_pages_open(admin_client, url, brands):  # noqa: ARG001
    assert admin_client.get(reverse(url)).status_code == 200
