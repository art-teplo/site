from contextlib import contextmanager
from contextvars import ContextVar

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .tasks import revalidate_frontend

_muted = ContextVar('revalidation_muted', default=False)


@contextmanager
def muted_revalidation():
    """Массовая правка: внутри сброс кэша не ставится в очередь, после выхода
    вызывающий сам зовёт revalidate_frontend.delay(тег) один раз."""
    token = _muted.set(True)
    try:
        yield
    finally:
        _muted.reset(token)


@receiver(post_save)
@receiver(post_delete)
def content_changed(sender, **_):
    tag = getattr(sender, 'cache_tag', None)
    if tag and not _muted.get():
        transaction.on_commit(lambda: revalidate_frontend.delay(tag))
