import json
from unittest import mock

import graphene
from django.utils.functional import SimpleLazyObject
from freezegun import freeze_time

from .....core.utils.json_serializer import CustomJsonEncoder
from .....post.error_codes import PostErrorCode
from .....post.models import PostType
from .....webhook.event_types import WebhookEventAsyncType
from .....webhook.payloads import generate_meta, generate_requestor
from ....tests.utils import assert_no_permission, get_graphql_content

POST_TYPE_UPDATE_MUTATION = """
    mutation PostTypeUpdate(
        $id: ID!, $input: PostTypeUpdateInput!
    ) {
        postTypeUpdate(id: $id, input: $input) {
            postType {
                id
                name
                slug
                attributes {
                    slug
                }
            }
            errors {
                code
                field
                message
                attributes
            }
        }
    }
"""


def test_post_type_update_as_staff(
    staff_api_client,
    post_type,
    permission_manage_post_types_and_attributes,
    author_post_attribute,
    size_post_attribute,
    tag_post_attribute,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    slug = "new-slug"
    name = "new-name"

    variables = {
        "id": graphene.Node.to_global_id("PostType", post_type.pk),
        "input": {
            "slug": slug,
            "name": name,
            "addAttributes": [
                graphene.Node.to_global_id("Attribute", author_post_attribute.pk)
            ],
            "removeAttributes": [
                graphene.Node.to_global_id("Attribute", size_post_attribute.pk)
            ],
        },
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_UPDATE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeUpdate"]
    errors = data["errors"]
    post_type_data = data["postType"]

    post_type.refresh_from_db()
    assert not errors
    assert post_type_data["name"] == name
    assert post_type_data["slug"] == slug
    assert {attr["slug"] for attr in post_type_data["attributes"]} == {
        tag_post_attribute.slug,
        author_post_attribute.slug,
    }


@freeze_time("2022-05-12 12:00:00")
@mock.patch("saleor.plugins.webhook.plugin.get_webhooks_for_event")
@mock.patch("saleor.plugins.webhook.plugin.trigger_webhooks_async")
def test_post_type_update_trigger_webhook(
    mocked_webhook_trigger,
    mocked_get_webhooks_for_event,
    any_webhook,
    staff_api_client,
    post_type,
    permission_manage_post_types_and_attributes,
    author_post_attribute,
    size_post_attribute,
    tag_post_attribute,
    settings,
):
    # given
    mocked_get_webhooks_for_event.return_value = [any_webhook]
    settings.PLUGINS = ["saleor.plugins.webhook.plugin.WebhookPlugin"]

    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    slug = "new-slug"

    variables = {
        "id": graphene.Node.to_global_id("PostType", post_type.pk),
        "input": {
            "slug": slug,
        },
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_UPDATE_MUTATION, variables)
    content = get_graphql_content(response)
    data = content["data"]["postTypeUpdate"]
    post_type.refresh_from_db()

    # then
    assert not data["errors"]
    assert data["postType"]["slug"] == slug
    mocked_webhook_trigger.assert_called_once_with(
        json.dumps(
            {
                "id": graphene.Node.to_global_id("PostType", post_type.id),
                "name": post_type.name,
                "slug": post_type.slug,
                "meta": generate_meta(
                    requestor_data=generate_requestor(
                        SimpleLazyObject(lambda: staff_user)
                    )
                ),
            },
            cls=CustomJsonEncoder,
        ),
        WebhookEventAsyncType.POST_TYPE_UPDATED,
        [any_webhook],
        post_type,
        SimpleLazyObject(lambda: staff_user),
    )


def test_post_type_update_as_staff_no_perm(staff_api_client, post_type):
    # given
    variables = {
        "id": graphene.Node.to_global_id("PostType", post_type.pk),
        "input": {"name": "New post type name"},
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_UPDATE_MUTATION, variables)

    # then
    assert_no_permission(response)


def test_post_type_update_as_app(
    staff_api_client,
    post_type,
    permission_manage_post_types_and_attributes,
    author_post_attribute,
    size_post_attribute,
    tag_post_attribute,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    slug = "new-slug"
    name = "new-name"

    variables = {
        "id": graphene.Node.to_global_id("PostType", post_type.pk),
        "input": {
            "slug": slug,
            "name": name,
            "addAttributes": [
                graphene.Node.to_global_id("Attribute", author_post_attribute.pk)
            ],
            "removeAttributes": [
                graphene.Node.to_global_id("Attribute", size_post_attribute.pk)
            ],
        },
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_UPDATE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeUpdate"]
    errors = data["errors"]
    post_type_data = data["postType"]

    post_type.refresh_from_db()
    assert not errors
    assert post_type_data["name"] == name
    assert post_type_data["slug"] == slug
    assert {attr["slug"] for attr in post_type_data["attributes"]} == {
        tag_post_attribute.slug,
        author_post_attribute.slug,
    }


def test_post_type_update_as_app_no_perm(app_api_client, post_type):
    # given
    variables = {
        "id": graphene.Node.to_global_id("PostType", post_type.pk),
        "input": {"name": "New post type name"},
    }

    # when
    response = app_api_client.post_graphql(POST_TYPE_UPDATE_MUTATION, variables)

    # then
    assert_no_permission(response)


def test_post_type_update_duplicated_attributes(
    staff_api_client,
    post_type,
    permission_manage_post_types_and_attributes,
    author_post_attribute,
    size_post_attribute,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    author_post_attr_id = graphene.Node.to_global_id(
        "Attribute", author_post_attribute.pk
    )
    size_post_att_id = graphene.Node.to_global_id("Attribute", size_post_attribute.pk)

    variables = {
        "id": graphene.Node.to_global_id("PostType", post_type.pk),
        "input": {
            "addAttributes": [author_post_attr_id],
            "removeAttributes": [author_post_attr_id, size_post_att_id],
        },
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_UPDATE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeUpdate"]
    errors = data["errors"]
    post_type_data = data["postType"]

    assert not post_type_data
    assert len(errors) == 1
    assert errors[0]["code"] == PostErrorCode.DUPLICATED_INPUT_ITEM.name
    assert errors[0]["field"] == "attributes"
    assert errors[0]["attributes"] == [author_post_attr_id]


def test_post_type_update_not_valid_attributes(
    staff_api_client,
    post_type,
    permission_manage_post_types_and_attributes,
    author_post_attribute,
    size_post_attribute,
    color_attribute,
    weight_attribute,
    size_attribute,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    variables = {
        "id": graphene.Node.to_global_id("PostType", post_type.pk),
        "input": {
            "addAttributes": [
                graphene.Node.to_global_id("Attribute", attr.pk)
                for attr in [author_post_attribute, color_attribute]
            ],
            "removeAttributes": [
                graphene.Node.to_global_id("Attribute", attr.pk)
                for attr in [size_post_attribute, weight_attribute, size_attribute]
            ],
        },
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_UPDATE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeUpdate"]
    errors = data["errors"]
    post_type_data = data["postType"]

    assert not post_type_data
    assert len(errors) == 2
    expected_errors = [
        {
            "code": PostErrorCode.INVALID.name,
            "field": "addAttributes",
            "message": mock.ANY,
            "attributes": [graphene.Node.to_global_id("Attribute", color_attribute.pk)],
        },
        {
            "code": PostErrorCode.INVALID.name,
            "field": "removeAttributes",
            "message": mock.ANY,
            "attributes": [
                graphene.Node.to_global_id("Attribute", attr.pk)
                for attr in [weight_attribute, size_attribute]
            ],
        },
    ]
    for error in errors:
        assert error in expected_errors


def test_post_type_update_empty_slug(
    staff_api_client, post_type, permission_manage_post_types_and_attributes
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    variables = {
        "id": graphene.Node.to_global_id("PostType", post_type.pk),
        "input": {"name": "New post type name", "slug": ""},
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_UPDATE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeUpdate"]
    errors = data["errors"]
    post_type_data = data["postType"]

    assert not post_type_data
    assert len(errors) == 1
    assert errors[0]["code"] == PostErrorCode.REQUIRED.name
    assert errors[0]["field"] == "slug"


def test_post_type_update_duplicated_slug(
    staff_api_client, post_type, permission_manage_post_types_and_attributes
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    slug = "duplicated-tag"
    PostType.objects.create(name="Test post type 2", slug=slug)

    variables = {
        "id": graphene.Node.to_global_id("PostType", post_type.pk),
        "input": {"name": "New post type name", "slug": slug},
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_UPDATE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeUpdate"]
    errors = data["errors"]
    post_type_data = data["postType"]

    assert not post_type_data
    assert len(errors) == 1
    assert errors[0]["code"] == PostErrorCode.UNIQUE.name
    assert errors[0]["field"] == "slug"


def test_post_type_update_multiple_errors(
    staff_api_client,
    post_type,
    permission_manage_post_types_and_attributes,
    author_post_attribute,
    size_post_attribute,
    color_attribute,
):
    """Ensure that if multiple errors occurred all will be raised."""

    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    color_attribute_id = graphene.Node.to_global_id("Attribute", color_attribute.pk)
    author_post_attr_id = graphene.Node.to_global_id(
        "Attribute", author_post_attribute.pk
    )
    size_post_att_id = graphene.Node.to_global_id("Attribute", size_post_attribute.pk)

    variables = {
        "id": graphene.Node.to_global_id("PostType", post_type.pk),
        "input": {
            "slug": "",
            "addAttributes": [author_post_attr_id, color_attribute_id],
            "removeAttributes": [author_post_attr_id, size_post_att_id],
        },
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_UPDATE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeUpdate"]
    errors = data["errors"]
    post_type_data = data["postType"]

    assert not post_type_data
    assert len(errors) == 3
    assert errors[0]["code"] == PostErrorCode.DUPLICATED_INPUT_ITEM.name
    assert errors[0]["field"] == "attributes"
    assert errors[0]["attributes"] == [author_post_attr_id]
