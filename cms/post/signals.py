from ..core.tasks import delete_from_storage_task, delete_post_media_task


def delete_post_media_image(sender, instance, **kwargs):
    if file := instance.image:
        delete_from_storage_task.delay(file.name)


def delete_post_all_media(sender, instance, **kwargs):
    if all_media := instance.media.all():
        for media in all_media:
            media.set_to_remove()
            delete_post_media_task.delay(media.id)
