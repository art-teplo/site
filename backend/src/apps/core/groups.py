from django.apps import apps
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ImproperlyConfigured

MANAGER_GROUP = 'Менеджер'

ALL = ('view', 'add', 'change', 'delete')

MANAGER_PERMISSIONS = {
    'leads.lead': ('view', 'change'),
    'content.sitesettings': ('view',),
    'content.openinghours': ('view',),
    'content.faq': ALL,
    'content.project': ALL,
    'content.projectphoto': ALL,
    'content.post': ALL,
    'content.promo': ALL,
    'content.showroomphoto': ALL,
    'catalog.category': ALL,
    'catalog.brand': ALL,
    'catalog.leadtime': ALL,
    'catalog.color': ALL,
    'catalog.series': ALL,
    'catalog.colorgroup': ALL,
    'catalog.variant': ALL,
    'catalog.seriesimage': ALL,
    'catalog.seriesfile': ALL,
    'catalog.showcase': ALL,
    'catalog.currencyrate': ('view',),
}


def manager_codenames():
    codenames = set()
    for label, actions in MANAGER_PERMISSIONS.items():
        app_label, model = label.split('.')
        codenames.update(f'{app_label}.{action}_{model}' for action in actions)
    return codenames


def manager_permissions():
    expected = manager_codenames()
    app_labels = {codename.split('.')[0] for codename in expected}
    found = {
        f'{p.content_type.app_label}.{p.codename}': p
        for p in Permission.objects.filter(
            content_type__app_label__in=app_labels,
        ).select_related('content_type')
    }
    missing = expected - found.keys()
    if missing:
        message = f'Нет прав для группы «{MANAGER_GROUP}»: {sorted(missing)}'
        raise ImproperlyConfigured(message)
    return [found[codename] for codename in expected]


def sync_manager_group(using='default', **kwargs):  # noqa: ARG001
    for app_config in apps.get_app_configs():
        create_permissions(app_config, verbosity=0, using=using)
    group, _ = Group.objects.using(using).get_or_create(name=MANAGER_GROUP)
    group.permissions.set(manager_permissions())
