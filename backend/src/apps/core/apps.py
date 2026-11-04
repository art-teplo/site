from django.apps import AppConfig, apps
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    name = 'apps.core'
    verbose_name = 'Общее'

    def ready(self):
        from apps.core.groups import sync_manager_group  # noqa: PLC0415

        post_migrate.connect(
            sync_manager_group,
            sender=apps.get_app_config('auth'),
        )
