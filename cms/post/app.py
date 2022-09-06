from django.apps import AppConfig
from django.db.models.signals import post_delete, pre_delete


class PostAppConfig(AppConfig):
    name = "cms.post"

    def ready(self):
        from .models import Category, Post, PostMedia
        from .signals import (
            delete_background_image,
            delete_post_all_media,
            delete_post_media_image,
        )

        # preventing duplicate signals
        post_delete.connect(
            delete_background_image,
            sender=Category,
            dispatch_uid="delete_category_background",
        )
        post_delete.connect(
            delete_post_media_image,
            sender=PostMedia,
            dispatch_uid="delete_post_media_image",
        )
        pre_delete.connect(
            delete_post_all_media,
            sender=Post,
            dispatch_uid="delete_post_all_media",
        )
