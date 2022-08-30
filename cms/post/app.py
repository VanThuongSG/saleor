from django.apps import AppConfig
from django.db.models.signals import post_delete, pre_delete


class PostAppConfig(AppConfig):
    name = "cms.post"

    def ready(self):
        from .models import Post, PostMedia
        from .signals import (
            delete_post_all_media,
            delete_post_media_image,
        )

        # preventing duplicate signals
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
