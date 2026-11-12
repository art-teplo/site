import io
import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.catalog.models import (
    Brand,
    Category,
    LeadTime,
    Series,
    SeriesImage,
    Showcase,
    Variant,
)
from apps.content.html import clean_html, read_minutes
from apps.content.models import (
    Faq,
    Post,
    Project,
    ProjectPhoto,
    Promo,
    ShowroomPhoto,
    SiteSettings,
    Tag,
)
from apps.content.tasks import revalidate_frontend

WEB_IMAGES = Path(__file__).resolve().parents[3] / 'web' / 'public' / 'images'


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / 'media'
    return settings.MEDIA_ROOT


def png(width=40, height=30):
    buffer = io.BytesIO()
    Image.new('RGB', (width, height)).save(buffer, 'PNG')
    return ContentFile(buffer.getvalue(), name='photo.png')


def with_image(obj, **size):
    obj.image.save('photo.png', png(**size), save=False)
    obj.save()
    return obj


@pytest.fixture
def make_project(db):  # noqa: ARG001
    def make(**fields):
        data = {
            'slug': 'kvartira',
            'title': 'Квартира 96 м²',
            'kind': Project.Kind.FLAT,
            'place': 'Минск',
            'image_alt': 'Гостиная',
            **fields,
        }
        return with_image(Project(**data))

    return make


@pytest.fixture
def make_post(db):  # noqa: ARG001
    def make(**fields):
        data = {
            'slug': 'statya',
            'title': 'Статья',
            'lead': 'Лид',
            'body': '<p>текст</p>',
            'image_alt': 'Обложка',
            **fields,
        }
        return with_image(Post(**data))

    return make


@pytest.fixture
def make_promo(db):  # noqa: ARG001
    def make(**fields):
        data = {
            'title': 'Акция',
            'body': '<p>текст</p>',
            'image_alt': 'Фото',
            **fields,
        }
        return with_image(Promo(**data))

    return make


# --- текст статьи ---


def test_clean_html_keeps_allowed_and_drops_the_rest():
    html = clean_html(
        '<h1>Заголовок</h1>'
        '<div>Абзац <strong>жирный</strong></div>'
        '<div><br></div>'
        '<p style="color:red" class="x">стиль</p>'
        '<script>alert(1)</script>'
        '<a href="javascript:alert(1)">плохая</a>'
        '<a href="https://art-teplo.by">хорошая</a>'
        '<img src="x.png">',
    )

    assert '<h2>Заголовок</h2>' in html
    assert '<p>Абзац <strong>жирный</strong></p>' in html
    assert '<p>стиль</p>' in html
    assert 'script' not in html
    assert 'alert' not in html
    assert '<img' not in html
    assert 'href="https://art-teplo.by"' in html
    assert 'rel="noopener noreferrer"' in html
    assert '<p></p>' not in html


def test_read_minutes():
    assert read_minutes('<p>коротко</p>') == 1
    assert read_minutes('<p>' + 'слово ' * 900 + '</p>') == 5


@pytest.mark.django_db
def test_post_body_cleaned_on_save(make_post):
    post = make_post(body='<h1>Раз</h1><script>x</script>')

    post.refresh_from_db()
    assert post.body == '<h2>Раз</h2>'


# --- API ---


@pytest.mark.django_db
def test_site_settings(client):
    site = SiteSettings.get_solo()
    site.address = 'ул. Леонида Беды, 39'
    site.phone = '+375293190286'
    site.email = 'info@art-teplo.by'
    site.instagram_url = 'https://www.instagram.com/artteplo_minsk/'
    site.yandex_org_id = 141315425329
    site.save()
    site.hours.create(days='Сб', time='10:00–17:00', position=1)
    site.hours.create(days='Пн–Пт', time='9:00–18:00', position=0)

    data = client.get(reverse('site')).json()

    assert data['phone'] == '+375 29 319-02-86'
    assert data['phone_href'] == 'tel:+375293190286'
    assert data['viber_url'] == 'viber://chat?number=%2B375293190286'
    assert data['instagram_handle'] == '@artteplo_minsk'
    assert data['yandex_org_id'] == 141315425329
    assert [row['days'] for row in data['hours']] == ['Пн–Пт', 'Сб']


@pytest.mark.django_db
def test_site_settings_empty(client):
    data = client.get(reverse('site')).json()

    assert data['phone'] == ''
    assert data['viber_url'] == ''
    assert data['yandex_org_id'] is None


@pytest.mark.django_db
def test_showroom_video_with_poster(client):
    site = SiteSettings.get_solo()
    site.showroom_video.save(
        'tour.mp4',
        ContentFile(b'\x00\x00\x00\x18ftypmp42', name='tour.mp4'),
        save=False,
    )
    site.showroom_poster.save('poster.png', png(160, 90), save=False)
    site.save()

    video = client.get(reverse('site')).json()['showroom_video']

    assert video['src'].startswith('/media/')
    assert video['src'].endswith('.mp4')
    poster = video['poster']
    assert (poster['width'], poster['height']) == (160, 90)


@pytest.mark.django_db
def test_showroom_video_empty(client):
    assert client.get(reverse('site')).json()['showroom_video'] is None


@pytest.mark.django_db
def test_showroom_video_rejects_other_formats():
    site = SiteSettings.get_solo()
    site.showroom_video.save(
        'tour.mov',
        ContentFile(b'0', name='tour.mov'),
        save=False,
    )

    with pytest.raises(ValidationError) as error:
        site.full_clean()

    assert 'showroom_video' in error.value.message_dict


@pytest.mark.django_db
def test_faq_in_order(client):
    Faq.objects.create(question='Второй', answer='б', position=2)
    Faq.objects.create(question='Первый', answer='а', position=1, on_home=True)

    data = client.get(reverse('faq-list')).json()

    assert [item['question'] for item in data] == ['Первый', 'Второй']
    assert data[0]['on_home'] is True


@pytest.mark.django_db
def test_projects_published_with_image(client, make_project):
    make_project()
    make_project(slug='skryt', is_published=False)

    data = client.get(reverse('project-list')).json()

    assert len(data) == 1
    assert data[0]['kind'] == 'квартира'
    image = data[0]['image']
    assert image['src'].startswith('/media/content_project/')
    assert (image['width'], image['height'], image['alt']) == (
        40,
        30,
        'Гостиная',
    )
    assert data[0]['photos'] == []


@pytest.mark.django_db
def test_project_series_slugs(client, make_project):
    brand = Brand.objects.create(slug='kzto', name='КЗТО', note='—')
    category = Category.objects.create(
        slug='radiatory',
        name='Радиаторы',
        short='—',
    )

    def make_series(slug, **fields):
        return Series.objects.create(
            brand=brand,
            category=category,
            slug=slug,
            name=slug,
            **fields,
        )

    project = make_project()
    project.series.set(
        [make_series('a'), make_series('hidden', is_published=False)],
    )

    data = client.get(reverse('project-list')).json()

    assert data[0]['series_slugs'] == ['a']


@pytest.mark.django_db
def test_project_photos_in_order(client, make_project):
    project = make_project()
    with_image(ProjectPhoto(project=project, image_alt='Спальня', position=2))
    with_image(ProjectPhoto(project=project, image_alt='Кухня', position=1))

    data = client.get(reverse('project-list')).json()

    assert [photo['alt'] for photo in data[0]['photos']] == [
        'Кухня',
        'Спальня',
    ]


@pytest.mark.django_db
def test_posts_list_and_detail(client, make_post):
    make_post()
    make_post(slug='chernovik', is_published=False)

    data = client.get(reverse('post-list')).json()
    assert [post['slug'] for post in data] == ['statya']
    assert 'body' not in data[0]
    assert data[0]['read_minutes'] == 1

    url = reverse('post-detail', args=['statya'])
    assert client.get(url).json()['body'] == '<p>текст</p>'
    hidden = reverse('post-detail', args=['chernovik'])
    assert client.get(hidden).status_code == 404


@pytest.mark.django_db
def test_promos_list_hides_drafts_and_ended(client, make_promo):
    today = timezone.localdate()
    make_promo(title='Бессрочная', position=2)
    make_promo(title='Последний день', ends_at=today, position=1)
    make_promo(title='Кончилась', ends_at=today - timedelta(days=1))
    make_promo(title='Черновик', is_published=False)

    data = client.get(reverse('promo-list')).json()

    assert [promo['title'] for promo in data] == [
        'Последний день',
        'Бессрочная',
    ]
    assert data[0]['ends_at'] == today.isoformat()
    assert data[1]['ends_at'] is None
    assert data[0]['image']['width'] == 40


@pytest.mark.django_db
def test_promo_body_cleaned_and_revalidates_blog(
    make_promo,
    django_capture_on_commit_callbacks,
):
    with (
        patch.object(revalidate_frontend, 'delay') as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        promo = make_promo(body='<h1>Раз</h1><script>x</script>')

    promo.refresh_from_db()
    assert promo.body == '<h2>Раз</h2>'
    delay.assert_called_with(Tag.POSTS)


# --- обновление фронта ---


@pytest.mark.django_db
def test_change_asks_frontend_to_revalidate(
    django_capture_on_commit_callbacks,
):
    with (
        patch.object(revalidate_frontend, 'delay') as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        faq = Faq.objects.create(question='В', answer='О')
        faq.delete()

    assert [call.args for call in delay.call_args_list] == [
        (Tag.FAQ,),
        (Tag.FAQ,),
    ]


def test_revalidate_posts_tag_with_secret(settings):
    settings.FRONTEND__REVALIDATE_URL = 'http://web:3000/api/revalidate'
    settings.FRONTEND__REVALIDATE_SECRET = 's3cret'

    with patch('apps.content.tasks.urlopen') as urlopen:
        revalidate_frontend.apply(args=[Tag.POSTS])

    request = urlopen.call_args.args[0]
    assert request.full_url == 'http://web:3000/api/revalidate'
    assert request.get_header('Authorization') == 'Bearer s3cret'
    assert json.loads(request.data) == {'tags': ['posts']}


def test_revalidate_not_retried_on_wrong_secret(settings):
    settings.FRONTEND__REVALIDATE_URL = 'http://web:3000/api/revalidate'
    error = HTTPError(
        'http://web:3000/api/revalidate', 401, 'Unauthorized', {}, None
    )

    with patch('apps.content.tasks.urlopen', side_effect=error) as urlopen:
        result = revalidate_frontend.apply(args=[Tag.POSTS])

    assert result.successful()
    assert urlopen.call_count == 1


def test_revalidate_skipped_without_url(settings):
    settings.FRONTEND__REVALIDATE_URL = ''

    with patch('apps.content.tasks.urlopen') as urlopen:
        revalidate_frontend.apply(args=[Tag.POSTS])

    urlopen.assert_not_called()


# --- демо-данные ---


@pytest.mark.django_db
def test_loaddemo_is_repeatable(media):
    call_command('loaddemo', images=WEB_IMAGES)
    call_command('loaddemo', images=WEB_IMAGES)

    assert Faq.objects.count() == 7
    assert Faq.objects.filter(on_home=True).count() == 4
    assert Project.objects.count() == 4
    assert Post.objects.count() == 3
    assert Promo.objects.count() == 1
    assert ShowroomPhoto.objects.count() == 5
    site = SiteSettings.get_solo()
    assert site.hours.count() == 3
    assert Post.objects.first().body.startswith('<h2>')
    assert Category.objects.count() == 4
    assert Brand.objects.filter(logo='').count() == 2
    assert LeadTime.objects.count() == 14
    files = [path for path in media.rglob('*') if path.is_file()]
    assert ProjectPhoto.objects.count() == 6
    # проекты, их доп. фото, статьи, акции, шоурум, категории, логотипы,
    # фото демо-серий
    assert len(files) == 4 + 6 + 3 + 1 + 5 + 4 + 5 + 9 + 8  # + фото типов


@pytest.mark.django_db
@pytest.mark.usefixtures('media')
def test_loaddemo_loads_series():
    call_command('loaddemo', images=WEB_IMAGES)
    call_command('loaddemo', images=WEB_IMAGES)

    series = Series.objects.filter(is_published=True)
    assert series.count() == 3
    for item in series:
        assert item.color_groups.filter(is_base=True).count() == 1
        assert item.showcases.count() >= 2
        assert all(show.variant_id for show in item.showcases.all())
    assert Variant.objects.count() == 16
    assert SeriesImage.objects.count() == 9
    assert Showcase.objects.count() == 6


# --- админка ---


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url',
    [
        'admin:content_sitesettings_change',
        'admin:content_faq_changelist',
        'admin:content_project_changelist',
        'admin:content_project_add',
        'admin:content_post_changelist',
        'admin:content_post_add',
        'admin:content_promo_changelist',
        'admin:content_promo_add',
        'admin:content_showroomphoto_changelist',
    ],
)
def test_admin_pages_open(admin_client, url):
    response = admin_client.get(reverse(url))

    assert response.status_code == 200


@pytest.mark.django_db
def test_post_admin_uses_editor_only_for_body(admin_client):
    html = admin_client.get(reverse('admin:content_post_add')).content.decode()

    assert html.count('<trix-editor') == 1
    assert 'input="wysiwyg-body"' in html
