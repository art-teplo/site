import os

from django.conf import settings
from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')

django_asgi_app = get_asgi_application()

# Статика запечена в образ при сборке (collectstatic), отдаём её отсюда.
# /media/ — только пока S3 выключен (локальная разработка).
routes = [
    Mount(
        '/static',
        StaticFiles(directory=settings.STATIC_ROOT),
        name='static',
    ),
]
if not settings.S3__ENABLED:
    routes.append(
        Mount(
            '/media',
            StaticFiles(directory=settings.MEDIA_ROOT),
            name='media',
        ),
    )

app = Starlette(debug=settings.DEBUG, routes=routes)

app.mount('/', django_asgi_app)  # pyright: ignore[reportArgumentType]
