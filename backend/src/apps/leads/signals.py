from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Lead


@receiver(post_delete, sender=Lead)
def delete_lead_file(sender, instance, **kwargs):  # noqa: ARG001
    if instance.file:
        instance.file.delete(save=False)
