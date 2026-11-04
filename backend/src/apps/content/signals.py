from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .tasks import revalidate_frontend


@receiver(post_save)
@receiver(post_delete)
def content_changed(sender, **_):
    # cache_tag есть только у моделей контента (models.Tag)
    tag = getattr(sender, 'cache_tag', None)
    if tag:
        transaction.on_commit(lambda: revalidate_frontend.delay(tag))
