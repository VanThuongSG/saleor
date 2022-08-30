from datetime import datetime, timedelta
from unittest import mock

import graphene
import pytz
from django.utils.functional import SimpleLazyObject
from django.utils.text import slugify
from freezegun import freeze_time

from .....post.error_codes import PostErrorCode
from .....post.models import Post, PostType
from .....tests.consts import TEST_SERVER_DOMAIN
from .....tests.utils import dummy_editorjs
from .....webhook.event_types import WebhookEventAsyncType
from .....webhook.payloads import generate_post_payload
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
                publishedAt
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
                        plainText
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


@freeze_time("2020-03-18 12:00:00")
def test_post_create_mutation(staff_api_client, permission_manage_posts, post_type):
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
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
    assert data["post"]["publishedAt"] == datetime.now(pytz.utc).isoformat()
    assert data["post"]["postType"]["id"] == post_type_id
    values = (
        data["post"]["attributes"][0]["values"][0]["slug"],
        data["post"]["attributes"][1]["values"][0]["slug"],
    )
    assert slugify(non_existent_attr_value) in values
    assert tag_value_slug in values


@freeze_time("2020-03-18 12:00:00")
def test_post_create_mutation_with_published_at_date(
    staff_api_client, permission_manage_posts, post_type
):
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    published_at = datetime.now(pytz.utc).replace(microsecond=0) + timedelta(days=5)
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
            "publishedAt": published_at,
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
    assert data["post"]["publishedAt"] == published_at.isoformat()
    assert data["post"]["postType"]["id"] == post_type_id
    values = (
        data["post"]["attributes"][0]["values"][0]["slug"],
        data["post"]["attributes"][1]["values"][0]["slug"],
    )
    assert slugify(non_existent_attr_value) in values
    assert tag_value_slug in values


@freeze_time("1914-06-28 10:50")
@mock.patch("saleor.plugins.webhook.plugin.get_webhooks_for_event")
@mock.patch("saleor.plugins.webhook.plugin.trigger_webhooks_async")
def test_post_create_trigger_post_webhook(
    mocked_webhook_trigger,
    mocked_get_webhooks_for_event,
    any_webhook,
    staff_api_client,
    permission_manage_posts,
    post_type,
    settings,
):
    mocked_get_webhooks_for_event.return_value = [any_webhook]
    settings.PLUGINS = ["saleor.plugins.webhook.plugin.WebhookPlugin"]

    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)
    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "slug": post_slug,
            "postType": post_type_id,
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
    assert data["post"]["postType"]["id"] == post_type_id
    post = Post.objects.first()
    expected_data = generate_post_payload(post, staff_api_client.user)

    mocked_webhook_trigger.assert_called_once_with(
        expected_data,
        WebhookEventAsyncType.POST_CREATED,
        [any_webhook],
        post,
        SimpleLazyObject(lambda: staff_api_client.user),
    )


def test_post_create_required_fields(
    staff_api_client, permission_manage_posts, post_type
):
    variables = {
        "input": {"postType": graphene.Node.to_global_id("PostType", post_type.pk)}
    }
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    errors = content["data"]["postCreate"]["errors"]

    assert len(errors) == 2
    assert {error["field"] for error in errors} == {"title", "slug"}
    assert {error["code"] for error in errors} == {PostErrorCode.REQUIRED.name}


def test_create_default_slug(staff_api_client, permission_manage_posts, post_type):
    # test creating root post
    title = "Spanish inquisition"
    variables = {
        "input": {
            "title": title,
            "postType": graphene.Node.to_global_id("PostType", post_type.pk),
        }
    }
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    assert not data["errors"]
    assert data["post"]["title"] == title
    assert data["post"]["slug"] == slugify(title)


def test_post_create_mutation_missing_required_attributes(
    staff_api_client, permission_manage_posts, post_type
):
    # given
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    # Default attributes defined in product_type fixture
    tag_attr = post_type.post_attributes.get(name="tag")
    tag_value_slug = tag_attr.values.first().slug
    tag_attr_id = graphene.Node.to_global_id("Attribute", tag_attr.id)

    # Add second attribute
    size_attr = post_type.post_attributes.get(name="Post size")
    size_attr.value_required = True
    size_attr.save(update_fields=["value_required"])

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "slug": post_slug,
            "postType": post_type_id,
            "attributes": [{"id": tag_attr_id, "values": [tag_value_slug]}],
        }
    }

    # when
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    errors = data["errors"]

    assert not data["post"]
    assert len(errors) == 1
    assert errors[0]["field"] == "attributes"
    assert errors[0]["code"] == PostErrorCode.REQUIRED.name
    assert errors[0]["attributes"] == [
        graphene.Node.to_global_id("Attribute", size_attr.pk)
    ]


def test_post_create_mutation_empty_attribute_value(
    staff_api_client, permission_manage_posts, post_type
):
    # given
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    # Default attributes defined in product_type fixture
    tag_attr = post_type.post_attributes.get(name="tag")
    tag_attr_id = graphene.Node.to_global_id("Attribute", tag_attr.id)

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "slug": post_slug,
            "postType": post_type_id,
            "attributes": [{"id": tag_attr_id, "values": ["  "]}],
        }
    }

    # when
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    errors = data["errors"]

    assert not data["post"]
    assert len(errors) == 1
    assert errors[0]["field"] == "attributes"
    assert errors[0]["code"] == PostErrorCode.REQUIRED.name
    assert errors[0]["attributes"] == [
        graphene.Node.to_global_id("Attribute", tag_attr.pk)
    ]


def test_create_post_with_file_attribute(
    staff_api_client, permission_manage_posts, post_type, post_file_attribute
):
    # given
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    post_type = PostType.objects.create(
        name="Test post type 2", slug="test-post-type-2"
    )
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    file_attribute_id = graphene.Node.to_global_id("Attribute", post_file_attribute.pk)
    post_type.post_attributes.add(post_file_attribute)
    attr_value = post_file_attribute.values.first()

    values_count = post_file_attribute.values.count()

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "slug": post_slug,
            "postType": post_type_id,
            "attributes": [{"id": file_attribute_id, "file": attr_value.file_url}],
        }
    }

    # when
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    errors = data["errors"]

    assert not errors
    assert data["post"]["title"] == post_title
    assert data["post"]["content"] == post_content
    assert data["post"]["slug"] == post_slug
    assert data["post"]["isPublished"] == post_is_published
    assert data["post"]["postType"]["id"] == post_type_id
    assert len(data["post"]["attributes"]) == 1
    expected_attr_data = {
        "attribute": {"slug": post_file_attribute.slug},
        "values": [
            {
                "slug": f"{attr_value.slug}-2",
                "name": attr_value.name,
                "file": {
                    "url": f"http://{TEST_SERVER_DOMAIN}/media/{attr_value.file_url}",
                    "contentType": None,
                },
                "reference": None,
                "plainText": None,
                "date": None,
                "dateTime": None,
            }
        ],
    }
    assert data["post"]["attributes"][0] == expected_attr_data

    post_file_attribute.refresh_from_db()
    assert post_file_attribute.values.count() == values_count + 1


def test_create_post_with_file_attribute_new_attribute_value(
    staff_api_client, permission_manage_posts, post_type, post_file_attribute
):
    # given
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    post_type = PostType.objects.create(
        name="Test post type 2", slug="test-post-type-2"
    )
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    file_attribute_id = graphene.Node.to_global_id("Attribute", post_file_attribute.pk)
    post_type.post_attributes.add(post_file_attribute)
    new_value = "new_test_value.txt"
    new_value_content_type = "text/plain"

    values_count = post_file_attribute.values.count()

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "slug": post_slug,
            "postType": post_type_id,
            "attributes": [
                {
                    "id": file_attribute_id,
                    "file": new_value,
                    "contentType": new_value_content_type,
                }
            ],
        }
    }

    # when
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    errors = data["errors"]

    assert not errors
    assert data["post"]["title"] == post_title
    assert data["post"]["content"] == post_content
    assert data["post"]["slug"] == post_slug
    assert data["post"]["isPublished"] == post_is_published
    assert data["post"]["postType"]["id"] == post_type_id
    assert len(data["post"]["attributes"]) == 1
    expected_attr_data = {
        "attribute": {"slug": post_file_attribute.slug},
        "values": [
            {
                "slug": slugify(new_value),
                "reference": None,
                "name": new_value,
                "file": {
                    "url": f"http://{TEST_SERVER_DOMAIN}/media/" + new_value,
                    "contentType": new_value_content_type,
                },
                "plainText": None,
                "date": None,
                "dateTime": None,
            }
        ],
    }
    assert data["post"]["attributes"][0] == expected_attr_data

    post_file_attribute.refresh_from_db()
    assert post_file_attribute.values.count() == values_count + 1


def test_create_post_with_file_attribute_not_required_no_file_url_given(
    staff_api_client, permission_manage_posts, post_type, post_file_attribute
):
    # given
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    post_type = PostType.objects.create(
        name="Test post type 2", slug="test-post-type-2"
    )
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    file_attribute_id = graphene.Node.to_global_id("Attribute", post_file_attribute.pk)
    post_type.post_attributes.add(post_file_attribute)

    post_file_attribute.value_required = False
    post_file_attribute.save(update_fields=["value_required"])

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "slug": post_slug,
            "postType": post_type_id,
            "attributes": [{"id": file_attribute_id, "file": ""}],
        }
    }

    # when
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
    assert data["post"]["postType"]["id"] == post_type_id
    assert len(data["post"]["attributes"]) == 1
    assert len(data["post"]["attributes"][0]["values"]) == 0


def test_create_post_with_file_attribute_required_no_file_url_given(
    staff_api_client, permission_manage_posts, post_type, post_file_attribute
):
    # given
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    post_type = PostType.objects.create(
        name="Test post type 2", slug="test-post-type-2"
    )
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    file_attribute_id = graphene.Node.to_global_id("Attribute", post_file_attribute.pk)
    post_type.post_attributes.add(post_file_attribute)

    post_file_attribute.value_required = True
    post_file_attribute.save(update_fields=["value_required"])

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "slug": post_slug,
            "postType": post_type_id,
            "attributes": [{"id": file_attribute_id, "file": ""}],
        }
    }

    # when
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )

    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    errors = data["errors"]
    assert not data["post"]
    assert len(errors) == 1
    assert errors[0]["code"] == PostErrorCode.REQUIRED.name
    assert errors[0]["field"] == "attributes"
    assert errors[0]["attributes"] == [file_attribute_id]


def test_create_post_with_post_reference_attribute(
    staff_api_client,
    permission_manage_posts,
    post_type,
    post_type_post_reference_attribute,
    post,
):
    # given
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    post_type = PostType.objects.create(
        name="Test post type 2", slug="test-post-type-2"
    )
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    ref_attribute_id = graphene.Node.to_global_id(
        "Attribute", post_type_post_reference_attribute.pk
    )
    post_type.post_attributes.add(post_type_post_reference_attribute)
    reference = graphene.Node.to_global_id("Post", post.pk)

    values_count = post_type_post_reference_attribute.values.count()

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "slug": post_slug,
            "postType": post_type_id,
            "attributes": [{"id": ref_attribute_id, "references": [reference]}],
        }
    }

    # when
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    errors = data["errors"]

    assert not errors
    assert data["post"]["title"] == post_title
    assert data["post"]["content"] == post_content
    assert data["post"]["slug"] == post_slug
    assert data["post"]["isPublished"] == post_is_published
    assert data["post"]["postType"]["id"] == post_type_id
    assert len(data["post"]["attributes"]) == 1
    post_id = data["post"]["id"]
    _, new_post_pk = graphene.Node.from_global_id(post_id)
    expected_attr_data = {
        "attribute": {"slug": post_type_post_reference_attribute.slug},
        "values": [
            {
                "slug": f"{new_post_pk}_{post.pk}",
                "file": None,
                "name": post.title,
                "reference": reference,
                "plainText": None,
                "date": None,
                "dateTime": None,
            }
        ],
    }
    assert data["post"]["attributes"][0] == expected_attr_data

    post_type_post_reference_attribute.refresh_from_db()
    assert post_type_post_reference_attribute.values.count() == values_count + 1


@freeze_time(datetime(2020, 5, 5, 5, 5, 5, tzinfo=pytz.utc))
def test_create_post_with_date_attribute(
    staff_api_client,
    permission_manage_posts,
    post_type,
    date_attribute,
    post,
):
    # given
    post_type.post_attributes.add(date_attribute)

    post_title = "test title"
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)
    date_attribute_id = graphene.Node.to_global_id("Attribute", date_attribute.id)
    date_time_value = datetime.now(tz=pytz.utc)
    date_value = date_time_value.date()

    variables = {
        "input": {
            "title": post_title,
            "postType": post_type_id,
            "attributes": [
                {"id": date_attribute_id, "date": date_value},
            ],
        }
    }

    # when
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    errors = data["errors"]

    assert not errors
    assert data["post"]["title"] == post_title
    assert data["post"]["postType"]["id"] == post_type_id
    post_id = data["post"]["id"]
    _, new_post_pk = graphene.Node.from_global_id(post_id)
    expected_attributes_data = {
        "attribute": {"slug": "release-date"},
        "values": [
            {
                "file": None,
                "reference": None,
                "plainText": None,
                "dateTime": None,
                "date": str(date_value),
                "name": str(date_value),
                "slug": f"{new_post_pk}_{date_attribute.id}",
            }
        ],
    }

    assert expected_attributes_data in data["post"]["attributes"]


@freeze_time(datetime(2020, 5, 5, 5, 5, 5, tzinfo=pytz.utc))
def test_create_post_with_date_time_attribute(
    staff_api_client,
    permission_manage_posts,
    post_type,
    date_time_attribute,
    post,
):
    # given
    post_type.post_attributes.add(date_time_attribute)

    post_title = "test title"
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)
    date_time_attribute_id = graphene.Node.to_global_id(
        "Attribute", date_time_attribute.id
    )
    date_time_value = datetime.now(tz=pytz.utc)
    variables = {
        "input": {
            "title": post_title,
            "postType": post_type_id,
            "attributes": [
                {"id": date_time_attribute_id, "dateTime": date_time_value},
            ],
        }
    }

    # when
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    errors = data["errors"]

    assert not errors
    assert data["post"]["title"] == post_title
    assert data["post"]["postType"]["id"] == post_type_id
    post_id = data["post"]["id"]
    _, new_post_pk = graphene.Node.from_global_id(post_id)
    expected_attributes_data = {
        "attribute": {"slug": "release-date-time"},
        "values": [
            {
                "file": None,
                "reference": None,
                "plainText": None,
                "dateTime": date_time_value.isoformat(),
                "date": None,
                "name": str(date_time_value),
                "slug": f"{new_post_pk}_{date_time_attribute.id}",
            }
        ],
    }

    assert expected_attributes_data in data["post"]["attributes"]


def test_create_post_with_plain_text_attribute(
    staff_api_client,
    permission_manage_posts,
    post_type,
    plain_text_attribute_post_type,
    post,
):
    # given
    post_type.post_attributes.add(plain_text_attribute_post_type)

    post_title = "test title"
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)
    plain_text_attribute_id = graphene.Node.to_global_id(
        "Attribute", plain_text_attribute_post_type.id
    )
    text = "test plain text attribute content"

    variables = {
        "input": {
            "title": post_title,
            "postType": post_type_id,
            "attributes": [
                {"id": plain_text_attribute_id, "plainText": text},
            ],
        }
    }

    # when
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    errors = data["errors"]

    assert not errors
    assert data["post"]["title"] == post_title
    assert data["post"]["postType"]["id"] == post_type_id
    post_id = data["post"]["id"]
    _, new_post_pk = graphene.Node.from_global_id(post_id)
    expected_attributes_data = {
        "attribute": {"slug": plain_text_attribute_post_type.slug},
        "values": [
            {
                "file": None,
                "reference": None,
                "dateTime": None,
                "date": None,
                "name": text,
                "plainText": text,
                "slug": f"{new_post_pk}_{plain_text_attribute_post_type.id}",
            }
        ],
    }

    assert expected_attributes_data in data["post"]["attributes"]


def test_create_post_with_post_reference_attribute_not_required_no_references_given(
    staff_api_client,
    permission_manage_posts,
    post_type,
    post_type_post_reference_attribute,
):
    # given
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    post_type = PostType.objects.create(
        name="Test post type 2", slug="test-post-type-2"
    )
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    file_attribute_id = graphene.Node.to_global_id(
        "Attribute", post_type_post_reference_attribute.pk
    )
    post_type.post_attributes.add(post_type_post_reference_attribute)

    post_type_post_reference_attribute.value_required = False
    post_type_post_reference_attribute.save(update_fields=["value_required"])

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "slug": post_slug,
            "postType": post_type_id,
            "attributes": [{"id": file_attribute_id, "file": ""}],
        }
    }

    # when
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
    assert data["post"]["postType"]["id"] == post_type_id
    assert len(data["post"]["attributes"]) == 1
    assert len(data["post"]["attributes"][0]["values"]) == 0


def test_create_post_with_post_reference_attribute_required_no_references_given(
    staff_api_client,
    permission_manage_posts,
    post_type,
    post_type_post_reference_attribute,
):
    # given
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    post_type = PostType.objects.create(
        name="Test post type 2", slug="test-post-type-2"
    )
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    file_attribute_id = graphene.Node.to_global_id(
        "Attribute", post_type_post_reference_attribute.pk
    )
    post_type.post_attributes.add(post_type_post_reference_attribute)

    post_type_post_reference_attribute.value_required = True
    post_type_post_reference_attribute.save(update_fields=["value_required"])

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "slug": post_slug,
            "postType": post_type_id,
            "attributes": [{"id": file_attribute_id, "file": ""}],
        }
    }

    # when
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )

    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    errors = data["errors"]
    assert not data["post"]
    assert len(errors) == 1
    assert errors[0]["code"] == PostErrorCode.REQUIRED.name
    assert errors[0]["field"] == "attributes"
    assert errors[0]["attributes"] == [file_attribute_id]


def test_create_post_with_product_reference_attribute(
    staff_api_client,
    permission_manage_posts,
    post_type,
    post_type_product_reference_attribute,
    product,
):
    # given
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    post_type = PostType.objects.create(
        name="Test post type 2", slug="test-post-type-2"
    )
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    ref_attribute_id = graphene.Node.to_global_id(
        "Attribute", post_type_product_reference_attribute.pk
    )
    post_type.post_attributes.add(post_type_product_reference_attribute)
    reference = graphene.Node.to_global_id("Product", product.pk)

    values_count = post_type_product_reference_attribute.values.count()

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "slug": post_slug,
            "postType": post_type_id,
            "attributes": [{"id": ref_attribute_id, "references": [reference]}],
        }
    }

    # when
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    errors = data["errors"]

    assert not errors
    assert data["post"]["title"] == post_title
    assert data["post"]["content"] == post_content
    assert data["post"]["slug"] == post_slug
    assert data["post"]["isPublished"] == post_is_published
    assert data["post"]["postType"]["id"] == post_type_id
    assert len(data["post"]["attributes"]) == 1
    post_id = data["post"]["id"]
    _, new_post_pk = graphene.Node.from_global_id(post_id)
    expected_attr_data = {
        "attribute": {"slug": post_type_product_reference_attribute.slug},
        "values": [
            {
                "slug": f"{new_post_pk}_{product.pk}",
                "file": None,
                "name": product.name,
                "reference": reference,
                "plainText": None,
                "dateTime": None,
                "date": None,
            }
        ],
    }
    assert data["post"]["attributes"][0] == expected_attr_data

    post_type_product_reference_attribute.refresh_from_db()
    assert post_type_product_reference_attribute.values.count() == values_count + 1


def test_create_post_with_product_reference_attribute_not_required_no_references_given(
    staff_api_client,
    permission_manage_posts,
    post_type,
    post_type_product_reference_attribute,
):
    # given
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    post_type = PostType.objects.create(
        name="Test post type 2", slug="test-post-type-2"
    )
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    file_attribute_id = graphene.Node.to_global_id(
        "Attribute", post_type_product_reference_attribute.pk
    )
    post_type.post_attributes.add(post_type_product_reference_attribute)

    post_type_product_reference_attribute.value_required = False
    post_type_product_reference_attribute.save(update_fields=["value_required"])

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "slug": post_slug,
            "postType": post_type_id,
            "attributes": [{"id": file_attribute_id, "file": ""}],
        }
    }

    # when
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
    assert data["post"]["postType"]["id"] == post_type_id
    assert len(data["post"]["attributes"]) == 1
    assert len(data["post"]["attributes"][0]["values"]) == 0


def test_create_post_with_product_reference_attribute_required_no_references_given(
    staff_api_client,
    permission_manage_posts,
    post_type,
    post_type_product_reference_attribute,
):
    # given
    post_slug = "test-slug"
    post_content = dummy_editorjs("test content", True)
    post_title = "test title"
    post_is_published = True
    post_type = PostType.objects.create(
        name="Test post type 2", slug="test-post-type-2"
    )
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    file_attribute_id = graphene.Node.to_global_id(
        "Attribute", post_type_product_reference_attribute.pk
    )
    post_type.post_attributes.add(post_type_product_reference_attribute)

    post_type_product_reference_attribute.value_required = True
    post_type_product_reference_attribute.save(update_fields=["value_required"])

    # test creating root post
    variables = {
        "input": {
            "title": post_title,
            "content": post_content,
            "isPublished": post_is_published,
            "slug": post_slug,
            "postType": post_type_id,
            "attributes": [{"id": file_attribute_id, "file": ""}],
        }
    }

    # when
    response = staff_api_client.post_graphql(
        CREATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )

    content = get_graphql_content(response)
    data = content["data"]["postCreate"]
    errors = data["errors"]
    assert not data["post"]
    assert len(errors) == 1
    assert errors[0]["code"] == PostErrorCode.REQUIRED.name
    assert errors[0]["field"] == "attributes"
    assert errors[0]["attributes"] == [file_attribute_id]
