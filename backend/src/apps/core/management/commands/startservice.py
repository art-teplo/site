import uvicorn
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Запускает backend (uvicorn, ASGI)'

    def handle(self, *args, **options):  # noqa: ARG002
        from django.conf import settings  # noqa: PLC0415

        # uvicorn.run, а не Server.run: только он поднимает несколько воркеров
        uvicorn.run(
            settings.ASGI_APPLICATION,
            host=settings.SERVER_HOST,
            port=settings.SERVER_PORT,
            workers=settings.SERVER_WORKERS,
            log_level='debug' if settings.DEBUG else 'info',
            # За nginx: доверяем X-Forwarded-* из docker-сети
            proxy_headers=True,
            forwarded_allow_ips='*',
            server_header=False,
        )
