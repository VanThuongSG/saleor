from ...post import models
from ..core.utils import from_global_id_or_error
from ..core.validators import validate_one_of_args_is_in_query
from ..utils import get_user_or_app_from_context
from .types import Post


def resolve_post(info, global_post_id=None, slug=None):
    validate_one_of_args_is_in_query("id", global_post_id, "slug", slug)
    requestor = get_user_or_app_from_context(info.context)

    if slug is not None:
        post = models.Post.objects.visible_to_user(requestor).filter(slug=slug).first()
    else:
        _type, post_pk = from_global_id_or_error(global_post_id, Post)
        post = models.Post.objects.visible_to_user(requestor).filter(pk=post_pk).first()
    return post


def resolve_posts(info):
    requestor = get_user_or_app_from_context(info.context)
    return models.Post.objects.visible_to_user(requestor)


def resolve_post_type(id):
    return models.PostType.objects.filter(id=id).first()


def resolve_post_types(_info):
    return models.PostType.objects.all()
