from datetime import datetime, timedelta

import graphene
import pytz

from .....post.error_codes import PostErrorCode
from .....post.models import Post
from ....tests.utils import get_graphql_content

UPDATE_POST_MUTATION = """
    mutation updatePost(
        $id: ID!, $input: PostInput!
    ) {
        postUpdate(
            id: $id, input: $input
        ) {
            post {
                id
                title
                slug
                isPublished
                publicationDate
                attributes {
                    attribute {
                        slug
                    }
                    values {
                        slug
                        name
                        reference
                        file {
                            url
                            contentType
                        }
                    }
                }
            }
            errors {
                field
                code
                message
            }
        }
    }
"""


def test_update_post_publication_date(
    staff_api_client, permission_manage_posts, post_type
):
    data = {
        "slug": "test-url",
        "title": "Test post",
        "post_type": post_type,
    }
    post = Post.objects.create(**data)
    publication_date = datetime.now(pytz.utc) + timedelta(days=5)
    post_id = graphene.Node.to_global_id("Post", post.id)
    variables = {
        "id": post_id,
        "input": {
            "isPublished": True,
            "slug": post.slug,
            "publicationDate": publication_date,
        },
    }
    response = staff_api_client.post_graphql(
        UPDATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]["isPublished"] is True
    assert data["post"]["publicationDate"] == publication_date.date().isoformat()


def test_post_update_mutation_publication_date_and_published_at_provided(
    staff_api_client, permission_manage_posts, post_type
):
    """Ensure an error is raised when publishedAt and publicationDate are both
    provided."""
    data = {
        "slug": "test-url",
        "title": "Test post",
        "post_type": post_type,
    }
    post = Post.objects.create(**data)
    published_at = datetime.now(pytz.utc) + timedelta(days=5)
    publication_date = datetime.now(pytz.utc) + timedelta(days=5)
    post_id = graphene.Node.to_global_id("Post", post.id)

    # test creating root post
    variables = {
        "id": post_id,
        "input": {
            "publishedAt": published_at,
            "publicationDate": publication_date,
        },
    }

    response = staff_api_client.post_graphql(
        UPDATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]
    assert not data["post"]
    assert len(data["errors"]) == 1
    assert data["errors"][0]["field"] == "publicationDate"
    assert data["errors"][0]["code"] == PostErrorCode.INVALID.name
