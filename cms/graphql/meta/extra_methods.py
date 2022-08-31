from ...post.models import Post


def extra_user_actions(instance, info, **data):
    info.context.plugins.customer_updated(instance)


def extra_post_actions(instance, info, **data):
    info.context.plugins.post_updated(instance)


MODEL_EXTRA_METHODS = {
    "Post": extra_post_actions,
    "User": extra_user_actions,
}


MODEL_EXTRA_PREFETCH = {
    "Post": Post.objects.prefetched_for_webhook,
}
