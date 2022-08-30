import graphene
import pytest
from django.utils import timezone
from freezegun import freeze_time

from .....post.models import Post
from .....tests.utils import dummy_editorjs
from ....tests.utils import get_graphql_content

QUERY_POSTS_WITH_FILTER = """
    query ($filter: PostFilterInput) {
        posts(first: 5, filter:$filter) {
            totalCount
            edges {
                node {
                    id
                }
            }
        }
    }
"""


@pytest.mark.parametrize(
    "post_filter, count",
    [
        ({"search": "Post1"}, 2),
        ({"search": "about"}, 1),
        ({"search": "test"}, 1),
        ({"search": "slug"}, 3),
        ({"search": "Post"}, 2),
    ],
)
def test_posts_query_with_filter(
    post_filter, count, staff_api_client, permission_manage_posts, post_type
):
    query = QUERY_POSTS_WITH_FILTER
    Post.objects.create(
        title="Post1",
        slug="slug_post_1",
        content=dummy_editorjs("Content for post 1"),
        post_type=post_type,
    )
    Post.objects.create(
        title="Post2",
        slug="slug_post_2",
        content=dummy_editorjs("Content for post 2"),
        post_type=post_type,
    )
    Post.objects.create(
        title="About",
        slug="slug_about",
        content=dummy_editorjs("About test content"),
        post_type=post_type,
    )
    variables = {"filter": post_filter}
    staff_api_client.user.user_permissions.add(permission_manage_posts)
    response = staff_api_client.post_graphql(query, variables)
    content = get_graphql_content(response)
    assert content["data"]["posts"]["totalCount"] == count


def test_posts_query_with_filter_by_post_type(
    staff_api_client, permission_manage_posts, post_type_list
):
    query = QUERY_POSTS_WITH_FILTER
    post_type_ids = [
        graphene.Node.to_global_id("PostType", post_type.id)
        for post_type in post_type_list
    ][:2]

    variables = {"filter": {"postTypes": post_type_ids}}
    staff_api_client.user.user_permissions.add(permission_manage_posts)
    response = staff_api_client.post_graphql(query, variables)
    content = get_graphql_content(response)
    assert content["data"]["posts"]["totalCount"] == 2


def test_posts_query_with_filter_by_ids(
    staff_api_client, permission_manage_posts, post_list, post_list_unpublished
):
    query = QUERY_POSTS_WITH_FILTER

    post_ids = [
        graphene.Node.to_global_id("Post", post.pk)
        for post in [post_list[0], post_list_unpublished[-1]]
    ]
    variables = {"filter": {"ids": post_ids}}
    staff_api_client.user.user_permissions.add(permission_manage_posts)
    response = staff_api_client.post_graphql(query, variables)
    content = get_graphql_content(response)
    assert content["data"]["posts"]["totalCount"] == len(post_ids)


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
            {"field": "PUBLISHED_AT", "direction": "ASC"},
            ["Post1", "Post2", "About"],
        ),
        (
            {"field": "PUBLISHED_AT", "direction": "DESC"},
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


POSTS_QUERY = """
    query {
        posts(first: 10) {
            edges {
                node {
                    id
                    title
                    slug
                    postType {
                        id
                    }
                    content
                    contentJson
                    attributes {
                        attribute {
                            slug
                        }
                        values {
                            id
                            slug
                        }
                    }
                }
            }
        }
    }
"""


def test_query_posts_by_staff(
    staff_api_client, post_list, post, permission_manage_posts
):
    """Ensure staff user with manage posts permission can query all posts,
    including unpublished posts."""
    # given
    unpublished_post = post
    unpublished_post.is_published = False
    unpublished_post.save(update_fields=["is_published"])

    post_count = Post.objects.count()

    staff_api_client.user.user_permissions.add(permission_manage_posts)

    # when
    response = staff_api_client.post_graphql(POSTS_QUERY)

    # then
    content = get_graphql_content(response)
    data = content["data"]["posts"]["edges"]
    assert len(data) == post_count


def test_query_posts_by_app(app_api_client, post_list, post, permission_manage_posts):
    """Ensure app with manage posts permission can query all posts,
    including unpublished posts."""
    # given
    unpublished_post = post
    unpublished_post.is_published = False
    unpublished_post.save(update_fields=["is_published"])

    post_count = Post.objects.count()

    app_api_client.app.permissions.add(permission_manage_posts)

    # when
    response = app_api_client.post_graphql(POSTS_QUERY)

    # then
    content = get_graphql_content(response)
    data = content["data"]["posts"]["edges"]
    assert len(data) == post_count


def test_query_posts_by_staff_no_perm(staff_api_client, post_list, post):
    """Ensure staff user without manage posts permission can query
    only published posts."""

    # given
    unpublished_post = post
    unpublished_post.is_published = False
    unpublished_post.save(update_fields=["is_published"])

    post_count = Post.objects.count()

    # when
    response = staff_api_client.post_graphql(POSTS_QUERY)

    # then
    content = get_graphql_content(response)
    data = content["data"]["posts"]["edges"]
    assert len(data) == post_count - 1


def test_query_posts_by_app_no_perm(app_api_client, post_list, post):
    """Ensure app without manage posts permission can query only published posts."""
    # given
    unpublished_post = post
    unpublished_post.is_published = False
    unpublished_post.save(update_fields=["is_published"])

    post_count = Post.objects.count()

    # when
    response = app_api_client.post_graphql(POSTS_QUERY)

    # then
    content = get_graphql_content(response)
    data = content["data"]["posts"]["edges"]
    assert len(data) == post_count - 1


def test_query_posts_by_customer(api_client, post_list, post):
    """Ensure customer user can query only published posts."""
    # given
    unpublished_post = post
    unpublished_post.is_published = False
    unpublished_post.save(update_fields=["is_published"])

    post_count = Post.objects.count()

    # when
    response = api_client.post_graphql(POSTS_QUERY)

    # then
    content = get_graphql_content(response)
    data = content["data"]["posts"]["edges"]
    assert len(data) == post_count - 1
