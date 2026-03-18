import os
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import Product, Variant, VariantImage


@receiver(post_delete, sender=Product)
def auto_delete_file_on_delete_product(sender, instance, **kwargs):
    """Deletes file from filesystem when corresponding Product object is deleted."""
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)


@receiver(post_delete, sender=Variant)
def auto_delete_file_on_delete_variant(sender, instance, **kwargs):
    """Deletes file from filesystem when corresponding Variant object is deleted."""
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)


@receiver(post_delete, sender=VariantImage)
def auto_delete_file_on_delete_variant_image(sender, instance, **kwargs):
    """Deletes file from filesystem when corresponding VariantImage object is deleted."""
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)


@receiver(pre_save, sender=Product)
def auto_delete_file_on_change_product(sender, instance, **kwargs):
    """Deletes old file from filesystem when corresponding Product object is updated with new file."""
    if not instance.pk:
        return False

    try:
        old_file = sender.objects.get(pk=instance.pk).image
    except sender.DoesNotExist:
        return False

    new_file = instance.image
    if not old_file == new_file:
        if old_file and os.path.isfile(old_file.path):
            os.remove(old_file.path)


@receiver(pre_save, sender=Variant)
def auto_delete_file_on_change_variant(sender, instance, **kwargs):
    """Deletes old file from filesystem when corresponding Variant object is updated with new file."""
    if not instance.pk:
        return False

    try:
        old_file = sender.objects.get(pk=instance.pk).image
    except sender.DoesNotExist:
        return False

    new_file = instance.image
    if not old_file == new_file:
        if old_file and os.path.isfile(old_file.path):
            os.remove(old_file.path)


@receiver(pre_save, sender=VariantImage)
def auto_delete_file_on_change_variant_image(sender, instance, **kwargs):
    """Deletes old file from filesystem when corresponding VariantImage object is updated with new file."""
    if not instance.pk:
        return False

    try:
        old_file = sender.objects.get(pk=instance.pk).image
    except sender.DoesNotExist:
        return False

    new_file = instance.image
    if not old_file == new_file:
        if old_file and os.path.isfile(old_file.path):
            os.remove(old_file.path)
