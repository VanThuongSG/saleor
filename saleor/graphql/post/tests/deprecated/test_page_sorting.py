import pytest
from django.utils import timezone
from freezegun import freeze_time

from .....post.models import Post
from .....tests.utils import dummy_editorjs
from ....tests.utils import get_graphql_content

QUERY_POST_WITH_SORT = """
    query ($sort_by: PostSortingInput!) {
        posts(first:5, sortBy: $sort_by) {
            edges{
                node{
                    title
                }
            }
        }
    }
"""


@pytest.mark.parametrize(
    "post_sort, result_order",
    [
        ({"field": "TITLE", "direction": "ASC"}, ["About", "Post1", "Post2"]),
        ({"field": "TITLE", "direction": "DESC"}, ["Post2", "Post1", "About"]),
        ({"field": "SLUG", "direction": "ASC"}, ["About", "Post2", "Post1"]),
        ({"field": "SLUG", "direction": "DESC"}, ["Post1", "Post2", "About"]),
        ({"field": "VISIBILITY", "direction": "ASC"}, ["Post2", "About", "Post1"]),
        ({"field": "VISIBILITY", "direction": "DESC"}, ["Post1", "About", "Post2"]),
        ({"field": "CREATION_DATE", "direction": "ASC"}, ["Post1", "About", "Post2"]),
        ({"field": "CREATION_DATE", "direction": "DESC"}, ["Post2", "About", "Post1"]),
        (
            {"field": "PUBLICATION_DATE", "direction": "ASC"},
            ["Post1", "Post2", "About"],
        ),
        (
            {"field": "PUBLICATION_DATE", "direction": "DESC"},
            ["About", "Post2", "Post1"],
        ),
    ],
)
def test_query_posts_with_sort(
    post_sort, result_order, staff_api_client, permission_manage_posts, post_type
):
    with freeze_time("2017-05-31 12:00:01"):
        Post.objects.create(
            title="Post1",
            slug="slug_post_1",
            content=dummy_editorjs("p1."),
            is_published=True,
            published_at=timezone.now().replace(year=2018, month=12, day=5),
            post_type=post_type,
        )
    with freeze_time("2019-05-31 12:00:01"):
        Post.objects.create(
            title="Post2",
            slug="post_2",
            content=dummy_editorjs("p2."),
            is_published=False,
            published_at=timezone.now().replace(year=2019, month=12, day=5),
            post_type=post_type,
        )
    with freeze_time("2018-05-31 12:00:01"):
        Post.objects.create(
            title="About",
            slug="about",
            content=dummy_editorjs("Ab."),
            is_published=True,
            post_type=post_type,
        )
    variables = {"sort_by": post_sort}
    staff_api_client.user.user_permissions.add(permission_manage_posts)
    response = staff_api_client.post_graphql(QUERY_POST_WITH_SORT, variables)
    content = get_graphql_content(response)
    posts = content["data"]["posts"]["edges"]

    for order, post_name in enumerate(result_order):
        assert posts[order]["node"]["title"] == post_name
