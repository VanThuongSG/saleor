import graphene

from .....post.models import Post
from ....tests.utils import get_graphql_content

MUTATION_PUBLISH_POSTS = """
    mutation publishManyPosts($ids: [ID!]!, $is_published: Boolean!) {
        postBulkPublish(ids: $ids, isPublished: $is_published) {
            count
        }
    }
    """


def test_bulk_publish(staff_api_client, post_list_unpublished, permission_manage_posts):
    post_list = post_list_unpublished
    assert not any(post.is_published for post in post_list)

    variables = {
        "ids": [graphene.Node.to_global_id("Post", post.id) for post in post_list],
        "is_published": True,
    }
    response = staff_api_client.post_graphql(
        MUTATION_PUBLISH_POSTS, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    post_list = Post.objects.filter(id__in=[post.pk for post in post_list])

    assert content["data"]["postBulkPublish"]["count"] == len(post_list)
    assert all(post.is_published for post in post_list)


def test_bulk_unpublish(staff_api_client, post_list, permission_manage_posts):
    assert all(post.is_published for post in post_list)
    variables = {
        "ids": [graphene.Node.to_global_id("Post", post.id) for post in post_list],
        "is_published": False,
    }
    response = staff_api_client.post_graphql(
        MUTATION_PUBLISH_POSTS, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    post_list = Post.objects.filter(id__in=[post.pk for post in post_list])

    assert content["data"]["postBulkPublish"]["count"] == len(post_list)
    assert not any(post.is_published for post in post_list)
