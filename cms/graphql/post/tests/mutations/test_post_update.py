from datetime import datetime, timedelta
from unittest import mock

import graphene
import pytest
import pytz
from django.utils import timezone
from django.utils.functional import SimpleLazyObject
from django.utils.text import slugify
from freezegun import freeze_time

from .....attribute.models import AttributeValue
from .....attribute.utils import associate_attribute_values_to_instance
from .....post.error_codes import PostErrorCode
from .....post.models import Post
from .....tests.consts import TEST_SERVER_DOMAIN
from .....tests.utils import dummy_editorjs
from .....webhook.event_types import WebhookEventAsyncType
from .....webhook.payloads import generate_post_payload
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
                publishedAt
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
                        plainText
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


def test_update_post(staff_api_client, permission_manage_posts, post):
    # given
    query = UPDATE_POST_MUTATION

    post_type = post.post_type
    tag_attr = post_type.post_attributes.get(name="tag")
    tag_attr_id = graphene.Node.to_global_id("Attribute", tag_attr.id)
    new_value = "Rainbow"

    post_title = post.title
    new_slug = "new-slug"
    assert new_slug != post.slug

    post_id = graphene.Node.to_global_id("Post", post.id)

    variables = {
        "id": post_id,
        "input": {
            "slug": new_slug,
            "isPublished": True,
            "attributes": [{"id": tag_attr_id, "values": [new_value]}],
        },
    }

    # when
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]["title"] == post_title
    assert data["post"]["slug"] == new_slug

    expected_attributes = []
    post_attr = post.attributes.all()
    for attr in post_type.post_attributes.all():
        if attr.slug != tag_attr.slug:
            values = [
                {
                    "slug": slug,
                    "file": None,
                    "name": name,
                    "reference": None,
                    "plainText": None,
                }
                for slug, name in post_attr.filter(
                    assignment__attribute=attr
                ).values_list("values__slug", "values__name")
            ]
        else:
            values = [
                {
                    "slug": slugify(new_value),
                    "file": None,
                    "name": new_value,
                    "plainText": None,
                    "reference": None,
                }
            ]
        attr_data = {
            "attribute": {"slug": attr.slug},
            "values": values,
        }
        expected_attributes.append(attr_data)

    attributes = data["post"]["attributes"]
    assert len(attributes) == len(expected_attributes)
    for attr_data in attributes:
        assert attr_data in expected_attributes


@mock.patch("cms.plugins.webhook.plugin.get_webhooks_for_event")
@mock.patch("cms.plugins.webhook.plugin.trigger_webhooks_async")
@freeze_time("2020-03-18 12:00:00")
def test_update_post_trigger_webhook(
    mocked_webhook_trigger,
    mocked_get_webhooks_for_event,
    any_webhook,
    staff_api_client,
    permission_manage_posts,
    post,
    settings,
):
    query = UPDATE_POST_MUTATION

    settings.PLUGINS = ["cms.plugins.webhook.plugin.WebhookPlugin"]
    mocked_get_webhooks_for_event.return_value = [any_webhook]

    post_title = post.title
    new_slug = "new-slug"
    assert new_slug != post.slug

    post_id = graphene.Node.to_global_id("Post", post.id)

    variables = {
        "id": post_id,
        "input": {
            "slug": new_slug,
            "isPublished": True,
        },
    }

    # when
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]["title"] == post_title
    assert data["post"]["slug"] == new_slug
    post.published_at = timezone.now()
    expected_data = generate_post_payload(post, staff_api_client.user)
    mocked_webhook_trigger.assert_called_once_with(
        expected_data,
        WebhookEventAsyncType.POST_UPDATED,
        [any_webhook],
        post,
        SimpleLazyObject(lambda: staff_api_client.user),
    )


def test_update_post_only_title(staff_api_client, permission_manage_posts, post):
    """Ensures that updating post field without providing attributes is allowed."""
    # given
    query = UPDATE_POST_MUTATION

    post_type = post.post_type
    post_title = post.title
    new_slug = "new-slug"
    assert new_slug != post.slug

    post_id = graphene.Node.to_global_id("Post", post.id)

    variables = {
        "id": post_id,
        "input": {
            "slug": new_slug,
            "isPublished": True,
        },
    }

    # when
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]["title"] == post_title
    assert data["post"]["slug"] == new_slug

    expected_attributes = []
    post_attr = post.attributes.all()
    for attr in post_type.post_attributes.all():
        values = [
            {
                "slug": slug,
                "file": None,
                "name": name,
                "reference": None,
                "plainText": None,
            }
            for slug, name in post_attr.filter(assignment__attribute=attr).values_list(
                "values__slug", "values__name"
            )
        ]
        attr_data = {
            "attribute": {"slug": attr.slug},
            "values": values,
        }
        expected_attributes.append(attr_data)

    attributes = data["post"]["attributes"]
    assert len(attributes) == len(expected_attributes)
    for attr_data in attributes:
        assert attr_data in expected_attributes


def test_update_post_with_file_attribute_value(
    staff_api_client, permission_manage_posts, post, post_file_attribute
):
    # given
    query = UPDATE_POST_MUTATION

    post_type = post.post_type
    post_type.post_attributes.add(post_file_attribute)
    new_value = "test.txt"
    post_file_attribute_id = graphene.Node.to_global_id(
        "Attribute", post_file_attribute.pk
    )

    post_id = graphene.Node.to_global_id("Post", post.id)

    variables = {
        "id": post_id,
        "input": {"attributes": [{"id": post_file_attribute_id, "file": new_value}]},
    }

    # when
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]
    updated_attribute = {
        "attribute": {"slug": post_file_attribute.slug},
        "values": [
            {
                "slug": slugify(new_value),
                "name": new_value,
                "plainText": None,
                "reference": None,
                "file": {
                    "url": f"http://{TEST_SERVER_DOMAIN}/media/" + new_value,
                    "contentType": None,
                },
            }
        ],
    }
    assert updated_attribute in data["post"]["attributes"]


def test_update_post_with_file_attribute_new_value_is_not_created(
    staff_api_client, permission_manage_posts, post, post_file_attribute
):
    # given
    query = UPDATE_POST_MUTATION

    post_type = post.post_type
    post_type.post_attributes.add(post_file_attribute)
    post_file_attribute_id = graphene.Node.to_global_id(
        "Attribute", post_file_attribute.pk
    )
    existing_value = post_file_attribute.values.first()
    associate_attribute_values_to_instance(post, post_file_attribute, existing_value)

    post_id = graphene.Node.to_global_id("Post", post.id)

    variables = {
        "id": post_id,
        "input": {
            "attributes": [
                {"id": post_file_attribute_id, "file": existing_value.file_url}
            ]
        },
    }

    # when
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]
    updated_attribute = {
        "attribute": {"slug": post_file_attribute.slug},
        "values": [
            {
                "slug": existing_value.slug,
                "name": existing_value.name,
                "plainText": None,
                "reference": None,
                "file": {
                    "url": (
                        f"http://{TEST_SERVER_DOMAIN}/media/{existing_value.file_url}"
                    ),
                    "contentType": existing_value.content_type,
                },
            }
        ],
    }
    assert updated_attribute in data["post"]["attributes"]


def test_update_post_clear_values(staff_api_client, permission_manage_posts, post):
    # given
    query = UPDATE_POST_MUTATION

    post_attr = post.attributes.first()
    attribute = post_attr.assignment.attribute
    attribute.value_required = False
    attribute.save(update_fields=["value_required"])

    post_file_attribute_id = graphene.Node.to_global_id("Attribute", attribute.pk)

    post_id = graphene.Node.to_global_id("Post", post.id)

    variables = {
        "id": post_id,
        "input": {"attributes": [{"id": post_file_attribute_id, "file": ""}]},
    }

    # when
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]
    assert not data["post"]["attributes"][0]["values"]

    with pytest.raises(post_attr._meta.model.DoesNotExist):
        post_attr.refresh_from_db()


def test_update_post_with_post_reference_attribute_new_value(
    staff_api_client,
    permission_manage_posts,
    post_list,
    post_type_post_reference_attribute,
):
    # given
    query = UPDATE_POST_MUTATION

    post = post_list[0]
    ref_post = post_list[1]
    post_type = post.post_type
    post_type.post_attributes.add(post_type_post_reference_attribute)

    values_count = post_type_post_reference_attribute.values.count()
    ref_attribute_id = graphene.Node.to_global_id(
        "Attribute", post_type_post_reference_attribute.pk
    )
    reference = graphene.Node.to_global_id("Post", ref_post.pk)

    post_id = graphene.Node.to_global_id("Post", post.id)

    variables = {
        "id": post_id,
        "input": {"attributes": [{"id": ref_attribute_id, "references": [reference]}]},
    }

    # when
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]
    updated_attribute = {
        "attribute": {"slug": post_type_post_reference_attribute.slug},
        "values": [
            {
                "slug": f"{post.pk}_{ref_post.pk}",
                "name": post.title,
                "file": None,
                "plainText": None,
                "reference": reference,
            }
        ],
    }
    assert updated_attribute in data["post"]["attributes"]

    post_type_post_reference_attribute.refresh_from_db()
    assert post_type_post_reference_attribute.values.count() == values_count + 1


def test_update_post_with_post_reference_attribute_existing_value(
    staff_api_client,
    permission_manage_posts,
    post_list,
    post_type_post_reference_attribute,
):
    # given
    query = UPDATE_POST_MUTATION

    post = post_list[0]
    ref_post = post_list[1]
    post_type = post.post_type
    post_type.post_attributes.add(post_type_post_reference_attribute)

    attr_value = AttributeValue.objects.create(
        attribute=post_type_post_reference_attribute,
        name=post.title,
        slug=f"{post.pk}_{ref_post.pk}",
        reference_post=ref_post,
    )
    associate_attribute_values_to_instance(
        post, post_type_post_reference_attribute, attr_value
    )

    values_count = post_type_post_reference_attribute.values.count()
    ref_attribute_id = graphene.Node.to_global_id(
        "Attribute", post_type_post_reference_attribute.pk
    )
    reference = graphene.Node.to_global_id("Post", ref_post.pk)

    post_id = graphene.Node.to_global_id("Post", post.id)

    variables = {
        "id": post_id,
        "input": {"attributes": [{"id": ref_attribute_id, "references": [reference]}]},
    }

    # when
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]
    updated_attribute = {
        "attribute": {"slug": post_type_post_reference_attribute.slug},
        "values": [
            {
                "slug": attr_value.slug,
                "file": None,
                "name": post.title,
                "plainText": None,
                "reference": reference,
            }
        ],
    }
    assert updated_attribute in data["post"]["attributes"]

    post_type_post_reference_attribute.refresh_from_db()
    assert post_type_post_reference_attribute.values.count() == values_count


def test_update_post_with_plain_text_attribute_new_value(
    staff_api_client,
    permission_manage_posts,
    post_list,
    plain_text_attribute_post_type,
):
    # given
    query = UPDATE_POST_MUTATION

    post = post_list[0]
    post_type = post.post_type
    post_type.post_attributes.add(plain_text_attribute_post_type)

    values_count = plain_text_attribute_post_type.values.count()
    attribute_id = graphene.Node.to_global_id(
        "Attribute", plain_text_attribute_post_type.pk
    )
    text = "test plain text attribute content"

    post_id = graphene.Node.to_global_id("Post", post.id)

    variables = {
        "id": post_id,
        "input": {"attributes": [{"id": attribute_id, "plainText": text}]},
    }

    # when
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]
    updated_attribute = {
        "attribute": {"slug": plain_text_attribute_post_type.slug},
        "values": [
            {
                "slug": f"{post.pk}_{plain_text_attribute_post_type.pk}",
                "name": text,
                "file": None,
                "reference": None,
                "plainText": text,
            }
        ],
    }
    assert updated_attribute in data["post"]["attributes"]

    plain_text_attribute_post_type.refresh_from_db()
    assert plain_text_attribute_post_type.values.count() == values_count + 1


def test_update_post_with_plain_text_attribute_existing_value(
    staff_api_client,
    permission_manage_posts,
    post_list,
    plain_text_attribute_post_type,
):
    # given
    query = UPDATE_POST_MUTATION

    post = post_list[0]
    post_type = post.post_type
    post_type.post_attributes.add(plain_text_attribute_post_type)

    values_count = plain_text_attribute_post_type.values.count()
    attribute_id = graphene.Node.to_global_id(
        "Attribute", plain_text_attribute_post_type.pk
    )
    attribute_value = plain_text_attribute_post_type.values.first()
    attribute_value.slug = f"{post.pk}_{plain_text_attribute_post_type.pk}"
    attribute_value.save(update_fields=["slug"])

    text = attribute_value.plain_text

    post_id = graphene.Node.to_global_id("Post", post.id)

    variables = {
        "id": post_id,
        "input": {"attributes": [{"id": attribute_id, "plainText": text}]},
    }

    # when
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]
    updated_attribute = {
        "attribute": {"slug": plain_text_attribute_post_type.slug},
        "values": [
            {
                "slug": attribute_value.slug,
                "name": text,
                "file": None,
                "reference": None,
                "plainText": text,
            }
        ],
    }
    assert updated_attribute in data["post"]["attributes"]

    plain_text_attribute_post_type.refresh_from_db()
    assert plain_text_attribute_post_type.values.count() == values_count


@pytest.mark.parametrize("value", ["", "  ", None])
def test_update_post_with_required_plain_text_attribute_empty_value(
    value,
    staff_api_client,
    permission_manage_posts,
    post_list,
    plain_text_attribute_post_type,
):
    # given
    query = UPDATE_POST_MUTATION

    post = post_list[0]
    post_type = post.post_type
    post_type.post_attributes.add(plain_text_attribute_post_type)

    attribute_id = graphene.Node.to_global_id(
        "Attribute", plain_text_attribute_post_type.pk
    )
    attribute_value = plain_text_attribute_post_type.values.first()
    attribute_value.slug = f"{post.pk}_{plain_text_attribute_post_type.pk}"
    attribute_value.save(update_fields=["slug"])

    plain_text_attribute_post_type.value_required = True
    plain_text_attribute_post_type.save(update_fields=["value_required"])

    post_id = graphene.Node.to_global_id("Post", post.id)

    variables = {
        "id": post_id,
        "input": {"attributes": [{"id": attribute_id, "plainText": value}]},
    }

    # when
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]
    errors = data["errors"]

    assert not data["post"]
    assert len(errors) == 1
    assert errors[0]["code"] == PostErrorCode.REQUIRED.name
    assert errors[0]["field"] == "attributes"


def test_update_post_with_product_reference_attribute_new_value(
    staff_api_client,
    permission_manage_posts,
    post,
    post_type_product_reference_attribute,
    product,
):
    # given
    query = UPDATE_POST_MUTATION

    post_type = post.post_type
    post_type.post_attributes.add(post_type_product_reference_attribute)

    values_count = post_type_product_reference_attribute.values.count()
    ref_attribute_id = graphene.Node.to_global_id(
        "Attribute", post_type_product_reference_attribute.pk
    )
    reference = graphene.Node.to_global_id("Product", product.pk)

    post_id = graphene.Node.to_global_id("Post", post.id)

    variables = {
        "id": post_id,
        "input": {"attributes": [{"id": ref_attribute_id, "references": [reference]}]},
    }

    # when
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]
    updated_attribute = {
        "attribute": {"slug": post_type_product_reference_attribute.slug},
        "values": [
            {
                "slug": f"{post.pk}_{product.pk}",
                "name": product.name,
                "file": None,
                "plainText": None,
                "reference": reference,
            }
        ],
    }
    assert updated_attribute in data["post"]["attributes"]

    post_type_product_reference_attribute.refresh_from_db()
    assert post_type_product_reference_attribute.values.count() == values_count + 1


def test_update_post_with_product_reference_attribute_existing_value(
    staff_api_client,
    permission_manage_posts,
    post,
    post_type_product_reference_attribute,
    product,
):
    # given
    query = UPDATE_POST_MUTATION

    post_type = post.post_type
    post_type.post_attributes.add(post_type_product_reference_attribute)

    attr_value = AttributeValue.objects.create(
        attribute=post_type_product_reference_attribute,
        name=post.title,
        slug=f"{post.pk}_{product.pk}",
        reference_product=product,
    )
    associate_attribute_values_to_instance(
        post, post_type_product_reference_attribute, attr_value
    )

    values_count = post_type_product_reference_attribute.values.count()
    ref_attribute_id = graphene.Node.to_global_id(
        "Attribute", post_type_product_reference_attribute.pk
    )
    reference = graphene.Node.to_global_id("Product", product.pk)

    post_id = graphene.Node.to_global_id("Post", post.id)

    variables = {
        "id": post_id,
        "input": {"attributes": [{"id": ref_attribute_id, "references": [reference]}]},
    }

    # when
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]
    updated_attribute = {
        "attribute": {"slug": post_type_product_reference_attribute.slug},
        "values": [
            {
                "slug": attr_value.slug,
                "file": None,
                "name": post.title,
                "reference": reference,
                "plainText": None,
            }
        ],
    }
    assert updated_attribute in data["post"]["attributes"]

    post_type_product_reference_attribute.refresh_from_db()
    assert post_type_product_reference_attribute.values.count() == values_count


@freeze_time("2020-03-18 12:00:00")
def test_public_post_sets_publication_date(
    staff_api_client, permission_manage_posts, post_type
):
    data = {
        "slug": "test-url",
        "title": "Test post",
        "content": dummy_editorjs("Content for post 1"),
        "is_published": False,
        "post_type": post_type,
    }
    post = Post.objects.create(**data)
    post_id = graphene.Node.to_global_id("Post", post.id)
    variables = {"id": post_id, "input": {"isPublished": True, "slug": post.slug}}
    response = staff_api_client.post_graphql(
        UPDATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]["isPublished"] is True
    assert data["post"]["publishedAt"] == datetime.now(pytz.utc).isoformat()


def test_update_post_publication_date(
    staff_api_client, permission_manage_posts, post_type
):
    data = {
        "slug": "test-url",
        "title": "Test post",
        "post_type": post_type,
    }
    post = Post.objects.create(**data)
    published_at = datetime.now(pytz.utc).replace(microsecond=0) + timedelta(days=5)
    post_id = graphene.Node.to_global_id("Post", post.id)
    variables = {
        "id": post_id,
        "input": {"isPublished": True, "slug": post.slug, "publishedAt": published_at},
    }
    response = staff_api_client.post_graphql(
        UPDATE_POST_MUTATION, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]

    assert not data["errors"]
    assert data["post"]["isPublished"] is True
    assert data["post"]["publishedAt"] == published_at.isoformat()


@pytest.mark.parametrize("slug_value", [None, ""])
def test_update_post_blank_slug_value(
    staff_api_client, permission_manage_posts, post, slug_value
):
    query = UPDATE_POST_MUTATION
    assert slug_value != post.slug

    post_id = graphene.Node.to_global_id("Post", post.id)
    variables = {"id": post_id, "input": {"slug": slug_value, "isPublished": True}}
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    errors = content["data"]["postUpdate"]["errors"]

    assert len(errors) == 1
    assert errors[0]["field"] == "slug"
    assert errors[0]["code"] == PostErrorCode.REQUIRED.name


@pytest.mark.parametrize("slug_value", [None, ""])
def test_update_post_with_title_value_and_without_slug_value(
    staff_api_client, permission_manage_posts, post, slug_value
):
    query = """
        mutation updatePost($id: ID!, $title: String, $slug: String) {
        postUpdate(id: $id, input: {title: $title, slug: $slug}) {
            post {
                id
                title
                slug
            }
            errors {
                field
                code
                message
            }
        }
    }
    """
    post_id = graphene.Node.to_global_id("Post", post.id)
    variables = {"id": post_id, "title": "test", "slug": slug_value}
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    errors = content["data"]["postUpdate"]["errors"]

    assert len(errors) == 1
    assert errors[0]["field"] == "slug"
    assert errors[0]["code"] == PostErrorCode.REQUIRED.name


UPDATE_POST_ATTRIBUTES_MUTATION = """
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
                attributes {
                    attribute {
                        slug
                    }
                    values {
                        id
                        slug
                        name
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


def test_update_post_change_attribute_values_ordering(
    staff_api_client,
    permission_manage_posts,
    post,
    product_list,
    post_type_product_reference_attribute,
):
    # given
    post_type = post.post_type
    post_type.post_attributes.set([post_type_product_reference_attribute])

    post_id = graphene.Node.to_global_id("Post", post.pk)

    attribute_id = graphene.Node.to_global_id(
        "Attribute", post_type_product_reference_attribute.pk
    )

    attr_value_1 = AttributeValue.objects.create(
        attribute=post_type_product_reference_attribute,
        name=product_list[0].name,
        slug=f"{post.pk}_{product_list[0].pk}",
        reference_product=product_list[0],
    )
    attr_value_2 = AttributeValue.objects.create(
        attribute=post_type_product_reference_attribute,
        name=product_list[1].name,
        slug=f"{post.pk}_{product_list[1].pk}",
        reference_product=product_list[1],
    )
    attr_value_3 = AttributeValue.objects.create(
        attribute=post_type_product_reference_attribute,
        name=product_list[2].name,
        slug=f"{post.pk}_{product_list[2].pk}",
        reference_product=product_list[2],
    )

    associate_attribute_values_to_instance(
        post,
        post_type_product_reference_attribute,
        attr_value_3,
        attr_value_2,
        attr_value_1,
    )

    assert list(
        post.attributes.first().postvalueassignment.values_list("value_id", flat=True)
    ) == [attr_value_3.pk, attr_value_2.pk, attr_value_1.pk]

    new_ref_order = [product_list[1], product_list[0], product_list[2]]
    variables = {
        "id": post_id,
        "input": {
            "attributes": [
                {
                    "id": attribute_id,
                    "references": [
                        graphene.Node.to_global_id("Product", ref.pk)
                        for ref in new_ref_order
                    ],
                }
            ]
        },
    }

    # when
    response = staff_api_client.post_graphql(
        UPDATE_POST_ATTRIBUTES_MUTATION,
        variables,
        permissions=[permission_manage_posts],
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postUpdate"]
    assert data["errors"] == []

    attributes = data["post"]["attributes"]

    assert len(attributes) == 1
    values = attributes[0]["values"]
    assert len(values) == 3
    assert [value["id"] for value in values] == [
        graphene.Node.to_global_id("AttributeValue", val.pk)
        for val in [attr_value_2, attr_value_1, attr_value_3]
    ]
    post.refresh_from_db()
    assert list(
        post.attributes.first().postvalueassignment.values_list("value_id", flat=True)
    ) == [attr_value_2.pk, attr_value_1.pk, attr_value_3.pk]


def test_paginate_posts(user_api_client, post, post_type):
    post.is_published = True
    data_02 = {
        "slug": "test02-url",
        "title": "Test post",
        "content": dummy_editorjs("Content for post 1"),
        "is_published": True,
        "post_type": post_type,
    }
    data_03 = {
        "slug": "test03-url",
        "title": "Test post",
        "content": dummy_editorjs("Content for post 1"),
        "is_published": True,
        "post_type": post_type,
    }

    Post.objects.create(**data_02)
    Post.objects.create(**data_03)
    query = """
        query PostsQuery {
            posts(first: 2) {
                edges {
                    node {
                        id
                        title
                    }
                }
            }
        }
        """
    response = user_api_client.post_graphql(query)
    content = get_graphql_content(response)
    posts_data = content["data"]["posts"]
    assert len(posts_data["edges"]) == 2
