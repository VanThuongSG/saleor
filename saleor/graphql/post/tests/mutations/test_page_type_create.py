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

POST_TYPE_CREATE_MUTATION = """
    mutation PostTypeCreate($name: String, $slug: String, $addAttributes: [ID!]) {
        postTypeCreate(input: {
            name: $name, slug: $slug, addAttributes: $addAttributes
        }) {
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


def test_post_type_create_as_staff(
    staff_api_client,
    tag_post_attribute,
    author_post_attribute,
    permission_manage_post_types_and_attributes,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    name = "Test post type"
    slug = "test-post-type"

    attributes = [author_post_attribute, tag_post_attribute]

    variables = {
        "name": name,
        "slug": slug,
        "addAttributes": [
            graphene.Node.to_global_id("Attribute", attr.pk) for attr in attributes
        ],
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_CREATE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeCreate"]
    post_type_data = data["postType"]
    errors = data["errors"]

    assert not errors
    assert post_type_data["name"] == name
    assert post_type_data["slug"] == slug
    assert len(post_type_data["attributes"]) == 2
    assert {attr_data["slug"] for attr_data in post_type_data["attributes"]} == {
        attr.slug for attr in attributes
    }


@freeze_time("2022-05-12 12:00:00")
@mock.patch("saleor.plugins.webhook.plugin.get_webhooks_for_event")
@mock.patch("saleor.plugins.webhook.plugin.trigger_webhooks_async")
def test_post_type_create_trigger_webhook(
    mocked_webhook_trigger,
    mocked_get_webhooks_for_event,
    any_webhook,
    staff_api_client,
    tag_post_attribute,
    author_post_attribute,
    permission_manage_post_types_and_attributes,
    settings,
):
    # given
    mocked_get_webhooks_for_event.return_value = [any_webhook]
    settings.PLUGINS = ["saleor.plugins.webhook.plugin.WebhookPlugin"]

    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    name = "Test post type"
    slug = "test-post-type"

    attributes = [author_post_attribute, tag_post_attribute]

    variables = {
        "name": name,
        "slug": slug,
        "addAttributes": [
            graphene.Node.to_global_id("Attribute", attr.pk) for attr in attributes
        ],
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_CREATE_MUTATION, variables)
    post_type = PostType.objects.last()

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeCreate"]

    assert not data["errors"]
    assert data["postType"]
    mocked_webhook_trigger.assert_called_once_with(
        json.dumps(
            {
                "id": graphene.Node.to_global_id("PostType", post_type.id),
                "name": post_type.name,
                "slug": post_type.slug,
                "meta": generate_meta(
                    requestor_data=generate_requestor(
                        SimpleLazyObject(lambda: staff_api_client.user)
                    )
                ),
            },
            cls=CustomJsonEncoder,
        ),
        WebhookEventAsyncType.POST_TYPE_CREATED,
        [any_webhook],
        post_type,
        SimpleLazyObject(lambda: staff_api_client.user),
    )


def test_post_type_create_as_staff_no_perm(
    staff_api_client, tag_post_attribute, author_post_attribute
):
    # given
    name = "Test post type"
    slug = "test-post-type"

    attributes = [author_post_attribute, tag_post_attribute]

    variables = {
        "name": name,
        "slug": slug,
        "addAttributes": [
            graphene.Node.to_global_id("Attribute", attr.pk) for attr in attributes
        ],
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_CREATE_MUTATION, variables)

    # then
    assert_no_permission(response)


def test_post_type_create_as_app(
    app_api_client, tag_post_attribute, permission_manage_post_types_and_attributes
):
    # given
    app = app_api_client.app
    app.permissions.add(permission_manage_post_types_and_attributes)

    name = "Test post type"
    slug = "test-post-type"

    variables = {
        "name": name,
        "slug": slug,
        "addAttributes": [
            graphene.Node.to_global_id("Attribute", tag_post_attribute.pk)
        ],
    }

    # when
    response = app_api_client.post_graphql(POST_TYPE_CREATE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeCreate"]
    post_type_data = data["postType"]
    errors = data["errors"]

    assert not errors
    assert post_type_data["name"] == name
    assert post_type_data["slug"] == slug
    assert len(post_type_data["attributes"]) == 1
    assert post_type_data["attributes"][0]["slug"] == tag_post_attribute.slug


def test_post_type_create_as_app_no_perm(app_api_client, tag_post_attribute):
    # given
    name = "Test post type"
    slug = "test-post-type"

    variables = {
        "name": name,
        "slug": slug,
        "addAttributes": [
            graphene.Node.to_global_id("Attribute", tag_post_attribute.pk)
        ],
    }

    # when
    response = app_api_client.post_graphql(POST_TYPE_CREATE_MUTATION, variables)

    # then
    assert_no_permission(response)


def test_post_type_create_unique_slug_generated(
    staff_api_client,
    tag_post_attribute,
    author_post_attribute,
    permission_manage_post_types_and_attributes,
):
    """Ensure that unique slug is generated when slug is not given."""

    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    name_1 = "Test post type"
    name_2 = "test post type"
    slug = "test-post-type"

    post_type = PostType.objects.create(name=name_1, slug=slug)

    attributes = [author_post_attribute, tag_post_attribute]

    variables = {
        "name": name_2,
        "addAttributes": [
            graphene.Node.to_global_id("Attribute", attr.pk) for attr in attributes
        ],
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_CREATE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeCreate"]
    post_type_data = data["postType"]
    errors = data["errors"]

    assert not errors
    assert PostType.objects.count() == 2
    assert post_type_data["id"] != graphene.Node.to_global_id("PostType", post_type.pk)
    assert post_type_data["name"] == name_2
    assert post_type_data["slug"] == "test-post-type-2"
    assert len(post_type_data["attributes"]) == 2
    assert {attr_data["slug"] for attr_data in post_type_data["attributes"]} == {
        attr.slug for attr in attributes
    }


def test_post_type_create_duplicated_slug(
    staff_api_client,
    tag_post_attribute,
    author_post_attribute,
    permission_manage_post_types_and_attributes,
):
    """Ensure that unique errors is raised when post type with given slug exists."""

    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    name_1 = "Test post type"
    name_2 = "test post type"
    slug = "test-post-type"

    PostType.objects.create(name=name_1, slug=slug)

    attributes = [author_post_attribute, tag_post_attribute]

    variables = {
        "name": name_2,
        "slug": slug,
        "addAttributes": [
            graphene.Node.to_global_id("Attribute", attr.pk) for attr in attributes
        ],
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_CREATE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeCreate"]
    post_type_data = data["postType"]
    errors = data["errors"]

    assert not post_type_data
    assert len(errors) == 1
    assert errors[0]["code"] == PostErrorCode.UNIQUE.name
    assert errors[0]["field"] == "slug"


def test_post_type_create_not_valid_attributes(
    staff_api_client,
    tag_post_attribute,
    color_attribute,
    size_attribute,
    permission_manage_post_types_and_attributes,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    name = "Test post type"
    slug = "test-post-type"

    attributes = [color_attribute, tag_post_attribute, size_attribute]

    variables = {
        "name": name,
        "slug": slug,
        "addAttributes": [
            graphene.Node.to_global_id("Attribute", attr.pk) for attr in attributes
        ],
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_CREATE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeCreate"]
    post_type_data = data["postType"]
    errors = data["errors"]

    assert not post_type_data
    assert len(errors) == 1
    assert errors[0]["code"] == PostErrorCode.INVALID.name
    assert errors[0]["field"] == "addAttributes"
    assert set(errors[0]["attributes"]) == {
        graphene.Node.to_global_id("Attribute", attr.pk)
        for attr in [color_attribute, size_attribute]
    }
