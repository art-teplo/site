from django.apps import AppConfig


class ContentConfig(AppConfig):
    name = 'apps.content'
    verbose_name = 'Сайт'

    def ready(self):
        from . import signals  # noqa: F401, PLC0415
