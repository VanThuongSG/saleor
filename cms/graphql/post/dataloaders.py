from collections import defaultdict

from ...post import PostMediaTypes
from ...post.models import Post, PostType, PostMedia
from ...thumbnail.models import Thumbnail
from ..core.dataloaders import DataLoader


class PostByIdLoader(DataLoader):
    context_key = "post_by_id"

    def batch_load(self, keys):
        posts = Post.objects.using(self.database_connection_name).in_bulk(keys)
        return [posts.get(post_id) for post_id in keys]


class PostTypeByIdLoader(DataLoader):
    context_key = "post_type_by_id"

    def batch_load(self, keys):
        post_types = PostType.objects.using(self.database_connection_name).in_bulk(keys)
        return [post_types.get(post_type_id) for post_type_id in keys]


class PostsByPostTypeIdLoader(DataLoader):
    """Loads posts by posts type ID."""

    context_key = "posts_by_posttype"

    def batch_load(self, keys):
        posts = Post.objects.using(self.database_connection_name).filter(
            post_type_id__in=keys
        )

        posttype_to_posts = defaultdict(list)
        for post in posts:
            posttype_to_posts[post.post_type_id].append(post)

        return [posttype_to_posts[key] for key in keys]


class ImagesByPostIdLoader(DataLoader):
    context_key = "images_by_post"

    def batch_load(self, keys):
        images = PostMedia.objects.using(self.database_connection_name).filter(
            post_id=keys,
            type=PostMediaTypes.IMAGE,
            to_remove=False,
        )
        images_map = defaultdict(list)
        for image in images.iterator():
            images_map[image.post_id].append(image)
        return [images_map[post_id] for post_id in keys]



class MediaByPostIdLoader(DataLoader):
    context_key = "media_by_post"

    def batch_load(self, keys):
        media = PostMedia.objects.using(self.database_connection_name).filter(
            post_id__in=keys,
            to_remove=False,
        )
        media_map = defaultdict(list)
        for media_obj in media.iterator():
            media_map[media_obj.post_id].append(media_obj)
        return [media_map[post_id] for post_id in keys]


class BaseThumbnailBySizeAndFormatLoader(DataLoader):
    model_name = None

    def batch_load(self, keys):
        model_name = self.model_name.lower()
        instance_ids = [id for id, _, _ in keys]
        lookup = {f"{model_name}_id__in": instance_ids}
        thumbnails = Thumbnail.objects.using(self.database_connection_name).filter(
            **lookup
        )
        thumbnails_by_instance_id_size_and_format_map = defaultdict()
        for thumbnail in thumbnails:
            format = thumbnail.format.lower() if thumbnail.format else None
            thumbnails_by_instance_id_size_and_format_map[
                (getattr(thumbnail, f"{model_name}_id"), thumbnail.size, format)
            ] = thumbnail
        return [thumbnails_by_instance_id_size_and_format_map.get(key) for key in keys]


class ThumbnailByPostMediaIdSizeAndFormatLoader(BaseThumbnailBySizeAndFormatLoader):
    context_key = "thumbnail_by_postmedia_size_and_format"
    model_name = "post_media"
