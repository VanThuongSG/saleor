from datetime import datetime, timedelta

import graphene
import pytz
from django.utils.text import slugify

from .....post.error_codes import PostErrorCode
from .....tests.utils import dummy_editorjs
from ....tests.utils import get_graphql_content

CREATE_POST_MUTATION = """
    mutation CreatePost(
        $input: PostCreateInput!
    ) {
        postCreate(input: $input) {
            post {
                id
                title
                content
                slug
                isPublished
                publicationDate
                postType {
                    id
                }
                attributes {
                    attribute {
                        slug
                    }
                    values {
                        slug
                        name
                        reference
                        date
                        dateTime
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
                attributes
            }
        }
    }
"""


def test_post_create_mutation_with_publication_date(
    staff_api_client, permission_manage_posts, post_type
):
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    publication_date = datetime.now(pytz.utc) + timedelta(days=5)
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    # Default attributes defined in product_type fixture
    tag_attr = post_type.post_attributes.get(name="tag")
    tag_value_slug = tag_attr.values.first().slug
    tag_attr_id = graphene.Node.to_global_id("Attribute", tag_attr.id)

    # Add second attribute
    size_attr = post_type.post_attributes.get(name="Post size")
    size_attr_id = graphene.Node.to_global_id("Attribute", size_attr.id)
    non_existent_attr_value = "New value"

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "publicationDate": publication_date,
            "slug": post_slug,
            "postType": post_type_id,
            "attributes": [
                {"id": tag_attr_id, "values": [tag_value_slug]},
                {"id": size_attr_id, "values": [non_existent_attr_value]},
            ],
        }
    }

    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    assert data["errors"] == []
    assert data["post"]["title"] == post_title
    assert data["post"]["content"] == post_content
    assert data["post"]["slug"] == post_slug
    assert data["post"]["isPublished"] == post_is_published
    assert data["post"]["publicationDate"] == publication_date.date().isoformat()
    assert data["post"]["postType"]["id"] == post_type_id
    values = (
        data["post"]["attributes"][0]["values"][0]["slug"],
        data["post"]["attributes"][1]["values"][0]["slug"],
    )
    assert slugify(non_existent_attr_value) in values
    assert tag_value_slug in values


def test_post_create_mutation_publication_date_and_published_at_provided(
    staff_api_client, permission_manage_posts, post_type
):
    """Ensure an error is raised when publishedAt and publicationDate are both
    provided."""
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    publication_date = datetime.now(pytz.utc) + timedelta(days=5)
    published_at = datetime.now(pytz.utc) + timedelta(days=5)
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "publishedAt": published_at,
            "publicationDate": publication_date,
            "slug": post_slug,
            "postType": post_type_id,
        }
    }

    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    assert not data["post"]
    assert len(data["errors"]) == 1
    assert data["errors"][0]["field"] == "publicationDate"
    assert data["errors"][0]["code"] == PostErrorCode.INVALID.name
