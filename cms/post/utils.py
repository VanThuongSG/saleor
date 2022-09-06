from typing import TYPE_CHECKING, Dict, Iterable, List, Union

from ..core.tracing import traced_atomic_transaction
from .models import Post

if TYPE_CHECKING:
    # flake8: noqa
    from django.db.models.query import QuerySet

    from .models import Category, Post




@traced_atomic_transaction()
def delete_categories(categories_ids: List[str], manager):
    """Delete categories and perform all necessary actions.

    Set posts of deleted categories as unpublished, delete categories
    and update posts minimal variant prices.
    """
    from .models import Category, Post

    categories = Category.objects.select_for_update().filter(pk__in=categories_ids)
    categories.prefetch_related("posts")

    posts = Post.objects.none()
    for category in categories:
        posts = posts | collect_categories_tree_posts(category)

    # ProductChannelListing.objects.filter(product__in=products).update(
    #     is_published=False, published_at=None
    # )
    posts = list(posts)

    category_instances = [cat for cat in categories]
    categories.delete()

    for category in category_instances:
        manager.category_deleted(category)

    for product in posts:
        manager.product_updated(product)


def collect_categories_tree_posts(category: "Category") -> "QuerySet[Post]":
    """Collect posts from all levels in category tree."""
    posts = category.posts.prefetched_for_webhook(single_object=False)  # type: ignore
    descendants = category.get_descendants()
    for descendant in descendants:
        posts = posts | descendant.posts.all()
    return posts
