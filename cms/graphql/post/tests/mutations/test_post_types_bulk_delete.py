from unittest import mock

import graphene
import pytest

from .....post.models import Post
from ....attribute.utils import associate_attribute_values_to_instance
from ....tests.utils import assert_no_permission, get_graphql_content

POST_TYPE_BULK_DELETE_MUTATION = """
    mutation PostTypeBulkDelete($ids: [ID!]!) {
        postTypeBulkDelete(ids: $ids) {
            count
            errors {
                code
                field
                message
            }
        }
    }
"""


def test_post_type_bulk_delete_by_staff(
    staff_api_client, post_type_list, permission_manage_post_types_and_attributes
):
    # given
    staff_api_client.user.user_permissions.add(
        permission_manage_post_types_and_attributes
    )

    post_type_count = len(post_type_list)

    posts_pks = list(
        Post.objects.filter(post_type__in=post_type_list).values_list("pk", flat=True)
    )

    variables = {
        "ids": [
            graphene.Node.to_global_id("PostType", post_type.pk)
            for post_type in post_type_list
        ]
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_BULK_DELETE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeBulkDelete"]

    assert not data["errors"]
    assert data["count"] == post_type_count

    assert not Post.objects.filter(pk__in=posts_pks)


@mock.patch("cms.plugins.webhook.plugin.get_webhooks_for_event")
@mock.patch("cms.plugins.webhook.plugin.trigger_webhooks_async")
def test_post_type_bulk_delete_trigger_webhooks(
    mocked_webhook_trigger,
    mocked_get_webhooks_for_event,
    any_webhook,
    staff_api_client,
    post_type_list,
    permission_manage_post_types_and_attributes,
    settings,
):
    # given
    mocked_get_webhooks_for_event.return_value = [any_webhook]
    settings.PLUGINS = ["cms.plugins.webhook.plugin.WebhookPlugin"]

    staff_api_client.user.user_permissions.add(
        permission_manage_post_types_and_attributes
    )

    post_type_count = len(post_type_list)
    variables = {
        "ids": [
            graphene.Node.to_global_id("PostType", post_type.pk)
            for post_type in post_type_list
        ]
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_BULK_DELETE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeBulkDelete"]

    assert not data["errors"]
    assert data["count"] == post_type_count
    mocked_webhook_trigger.call_count == post_type_count


def test_post_type_bulk_delete_by_staff_no_perm(
    staff_api_client, post_type_list, permission_manage_post_types_and_attributes
):
    # given
    variables = {
        "ids": [
            graphene.Node.to_global_id("PostType", post_type.pk)
            for post_type in post_type_list
        ]
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_BULK_DELETE_MUTATION, variables)

    # then
    assert_no_permission(response)


def test_post_type_bulk_delete_by_app(
    app_api_client, post_type_list, permission_manage_post_types_and_attributes
):
    # given
    app_api_client.app.permissions.add(permission_manage_post_types_and_attributes)

    post_type_count = len(post_type_list)

    posts_pks = list(
        Post.objects.filter(post_type__in=post_type_list).values_list("pk", flat=True)
    )

    variables = {
        "ids": [
            graphene.Node.to_global_id("PostType", post_type.pk)
            for post_type in post_type_list
        ]
    }

    # when
    response = app_api_client.post_graphql(POST_TYPE_BULK_DELETE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeBulkDelete"]

    assert not data["errors"]
    assert data["count"] == post_type_count

    assert not Post.objects.filter(pk__in=posts_pks)


def test_post_type_bulk_delete_by_app_no_perm(
    app_api_client, post_type_list, permission_manage_post_types_and_attributes
):
    # given
    variables = {
        "ids": [
            graphene.Node.to_global_id("PostType", post_type.pk)
            for post_type in post_type_list
        ]
    }

    # when
    response = app_api_client.post_graphql(POST_TYPE_BULK_DELETE_MUTATION, variables)

    # then
    assert_no_permission(response)


def test_post_type_bulk_delete_with_file_attribute(
    app_api_client,
    post_type_list,
    post_file_attribute,
    permission_manage_post_types_and_attributes,
):
    # given
    app_api_client.app.permissions.add(permission_manage_post_types_and_attributes)

    post_type = post_type_list[1]

    post_type_count = len(post_type_list)

    post = Post.objects.filter(post_type=post_type.pk)[0]

    value = post_file_attribute.values.first()
    post_type.post_attributes.add(post_file_attribute)
    associate_attribute_values_to_instance(post, post_file_attribute, value)

    posts_pks = list(
        Post.objects.filter(post_type__in=post_type_list).values_list("pk", flat=True)
    )

    variables = {
        "ids": [
            graphene.Node.to_global_id("PostType", post_type.pk)
            for post_type in post_type_list
        ]
    }
    # when
    response = app_api_client.post_graphql(POST_TYPE_BULK_DELETE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeBulkDelete"]

    assert not data["errors"]
    assert data["count"] == post_type_count

    with pytest.raises(post_type._meta.model.DoesNotExist):
        post_type.refresh_from_db()
    with pytest.raises(value._meta.model.DoesNotExist):
        value.refresh_from_db()

    assert not Post.objects.filter(pk__in=posts_pks)


def test_post_type_bulk_delete_by_app_with_invalid_ids(
    app_api_client, post_type_list, permission_manage_post_types_and_attributes
):
    # given
    variables = {
        "ids": [
            graphene.Node.to_global_id("PostType", post_type.pk)
            for post_type in post_type_list
        ]
    }
    variables["ids"][0] = "invalid_id"

    # when
    response = app_api_client.post_graphql(
        POST_TYPE_BULK_DELETE_MUTATION,
        variables,
        permissions=[permission_manage_post_types_and_attributes],
    )

    # then
    content = get_graphql_content(response)
    errors = content["data"]["postTypeBulkDelete"]["errors"][0]

    assert errors["code"] == "GRAPHQL_ERROR"
