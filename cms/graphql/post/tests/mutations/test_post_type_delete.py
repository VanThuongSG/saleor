import json
from unittest import mock

import graphene
import pytest
from django.utils.functional import SimpleLazyObject
from freezegun import freeze_time

from .....attribute.utils import associate_attribute_values_to_instance
from .....core.utils.json_serializer import CustomJsonEncoder
from .....post.models import Post
from .....webhook.event_types import WebhookEventAsyncType
from .....webhook.payloads import generate_meta, generate_requestor
from ....tests.utils import assert_no_permission, get_graphql_content

DELETE_POST_TYPE_MUTATION = """
    mutation DeletePostType($id: ID!) {
        postTypeDelete(id: $id) {
            postType {
                id
                name
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


def test_post_type_delete_by_staff(
    staff_api_client, post_type, post, permission_manage_post_types_and_attributes
):
    # given
    staff_api_client.user.user_permissions.add(
        permission_manage_post_types_and_attributes
    )

    posts_pks = list(post_type.posts.values_list("pk", flat=True))

    assert posts_pks

    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    variables = {"id": post_type_id}

    # when
    response = staff_api_client.post_graphql(DELETE_POST_TYPE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeDelete"]

    assert not data["errors"]
    assert data["postType"]["id"] == post_type_id

    with pytest.raises(post_type._meta.model.DoesNotExist):
        post_type.refresh_from_db()

    # ensure that corresponding posts has been removed
    assert not Post.objects.filter(pk__in=posts_pks)


@freeze_time("2022-05-12 12:00:00")
@mock.patch("cms.plugins.webhook.plugin.get_webhooks_for_event")
@mock.patch("cms.plugins.webhook.plugin.trigger_webhooks_async")
def test_post_type_delete_trigger_webhook(
    mocked_webhook_trigger,
    mocked_get_webhooks_for_event,
    any_webhook,
    staff_api_client,
    post_type,
    post,
    permission_manage_post_types_and_attributes,
    settings,
):
    # given
    mocked_get_webhooks_for_event.return_value = [any_webhook]
    settings.PLUGINS = ["cms.plugins.webhook.plugin.WebhookPlugin"]

    staff_api_client.user.user_permissions.add(
        permission_manage_post_types_and_attributes
    )
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    # when
    response = staff_api_client.post_graphql(
        DELETE_POST_TYPE_MUTATION, {"id": post_type_id}
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeDelete"]

    assert not data["errors"]
    assert data["postType"]["id"] == post_type_id
    mocked_webhook_trigger.assert_called_once_with(
        json.dumps(
            {
                "id": post_type_id,
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
        WebhookEventAsyncType.POST_TYPE_DELETED,
        [any_webhook],
        post_type,
        SimpleLazyObject(lambda: staff_api_client.user),
    )


def test_post_type_delete_by_staff_no_perm(
    staff_api_client, post_type, post, permission_manage_post_types_and_attributes
):
    # given
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    variables = {"id": post_type_id}

    # when
    response = staff_api_client.post_graphql(DELETE_POST_TYPE_MUTATION, variables)

    # then
    assert_no_permission(response)


def test_post_type_delete_by_app(
    app_api_client, post_type, post, permission_manage_post_types_and_attributes
):
    # given
    app_api_client.app.permissions.add(permission_manage_post_types_and_attributes)

    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    posts_pks = list(post_type.posts.values_list("pk", flat=True))

    assert posts_pks

    variables = {"id": post_type_id}

    # when
    response = app_api_client.post_graphql(DELETE_POST_TYPE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeDelete"]

    assert not data["errors"]
    assert data["postType"]["id"] == post_type_id

    with pytest.raises(post_type._meta.model.DoesNotExist):
        post_type.refresh_from_db()

    # ensure that corresponding posts has been removed
    assert not Post.objects.filter(pk__in=posts_pks)


def test_post_type_delete_by_app_no_perm(
    app_api_client, post_type, post, permission_manage_post_types_and_attributes
):
    # given
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    variables = {"id": post_type_id}

    # when
    response = app_api_client.post_graphql(DELETE_POST_TYPE_MUTATION, variables)

    # then
    assert_no_permission(response)


def test_post_type_delete_with_file_attributes(
    staff_api_client,
    post_type,
    post,
    post_file_attribute,
    permission_manage_post_types_and_attributes,
):
    # given
    staff_api_client.user.user_permissions.add(
        permission_manage_post_types_and_attributes
    )
    post_type = post.post_type
    post_type.post_attributes.add(post_file_attribute)

    value = post_file_attribute.values.first()
    associate_attribute_values_to_instance(post, post_file_attribute, value)
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)

    variables = {"id": post_type_id}

    # when
    response = staff_api_client.post_graphql(DELETE_POST_TYPE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeDelete"]

    assert not data["errors"]
    assert data["postType"]["id"] == post_type_id

    with pytest.raises(post_type._meta.model.DoesNotExist):
        post_type.refresh_from_db()
    with pytest.raises(value._meta.model.DoesNotExist):
        value.refresh_from_db()
