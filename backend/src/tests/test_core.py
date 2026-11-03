import pytest
from django.db import connection


@pytest.mark.django_db
def test_health_ok(client):
    response = client.get('/api/health/')

    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


@pytest.mark.django_db
def test_health_reports_broken_db(client, monkeypatch):
    def broken_cursor():
        raise RuntimeError

    monkeypatch.setattr(connection, 'cursor', broken_cursor)

    response = client.get('/api/health/')

    assert response.status_code == 503
    assert response.json()['db'] == 'error'


@pytest.mark.django_db
def test_admin_on_custom_path(client, settings):
    response = client.get(f'/{settings.ADMIN_PATH}/login/')

    assert response.status_code == 200


@pytest.mark.django_db
def test_schema_closed_for_anonymous(client):
    response = client.get('/api/schema/')

    assert response.status_code == 403
