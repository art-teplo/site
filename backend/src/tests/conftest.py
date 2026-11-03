import pytest


@pytest.fixture(autouse=True)
def _plain_static_storage(settings):
    # Manifest-хранилище требует collectstatic; в тестах статику не собираем
    settings.STORAGES = {
        **settings.STORAGES,
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
