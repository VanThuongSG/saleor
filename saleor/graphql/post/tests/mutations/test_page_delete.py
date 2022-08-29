from unittest import mock

import graphene
import pytest
from django.utils.functional import SimpleLazyObject
from freezegun import freeze_time

from .....attribute.models import AttributeValue
from .....attribute.utils import associate_attribute_values_to_instance
from .....webhook.event_types import WebhookEventAsyncType
from .....webhook.payloads import generate_post_payload
from ....tests.utils import get_graphql_content

POST_DELETE_MUTATION = """
    mutation DeletePost($id: ID!) {
        postDelete(id: $id) {
            post {
                title
                id
            }
            errors {
                field
                code
                message
            }
        }
    }
"""


def test_post_delete_mutation(staff_api_client, post, permission_manage_posts):
    variables = {"id": graphene.Node.to_global_id("Post", post.id)}
    response = staff_api_client.post_graphql(
        POST_DELETE_MUTATION, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postDelete"]
    assert data["post"]["title"] == post.title
    with pytest.raises(post._meta.model.DoesNotExist):
        post.refresh_from_db()


@freeze_time("1914-06-28 10:50")
@mock.patch("saleor.plugins.webhook.plugin.get_webhooks_for_event")
@mock.patch("saleor.plugins.webhook.plugin.trigger_webhooks_async")
def test_post_delete_trigger_webhook(
    mocked_webhook_trigger,
    mocked_get_webhooks_for_event,
    any_webhook,
    staff_api_client,
    post,
    permission_manage_posts,
    settings,
):
    mocked_get_webhooks_for_event.return_value = [any_webhook]
    settings.PLUGINS = ["saleor.plugins.webhook.plugin.WebhookPlugin"]
    variables = {"id": graphene.Node.to_global_id("Post", post.id)}
    response = staff_api_client.post_graphql(
        POST_DELETE_MUTATION, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postDelete"]
    assert data["post"]["title"] == post.title
    with pytest.raises(post._meta.model.DoesNotExist):
        post.refresh_from_db()
    expected_data = generate_post_payload(post, staff_api_client.user)
    mocked_webhook_trigger.assert_called_once_with(
        expected_data,
        WebhookEventAsyncType.POST_DELETED,
        [any_webhook],
        post,
        SimpleLazyObject(lambda: staff_api_client.user),
    )


def test_post_delete_with_file_attribute(
    staff_api_client,
    post,
    permission_manage_posts,
    post_file_attribute,
):
    # given
    post_type = post.post_type
    post_type.post_attributes.add(post_file_attribute)
    existing_value = post_file_attribute.values.first()
    associate_attribute_values_to_instance(post, post_file_attribute, existing_value)

    variables = {"id": graphene.Node.to_global_id("Post", post.id)}

    # when
    response = staff_api_client.post_graphql(
        POST_DELETE_MUTATION, variables, permissions=[permission_manage_posts]
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postDelete"]
    assert data["post"]["title"] == post.title
    with pytest.raises(post._meta.model.DoesNotExist):
        post.refresh_from_db()
    with pytest.raises(existing_value._meta.model.DoesNotExist):
        existing_value.refresh_from_db()


def test_post_delete_removes_reference_to_product(
    product_type_post_reference_attribute,
    post,
    product_type,
    product,
    staff_api_client,
    permission_manage_posts,
):
    query = POST_DELETE_MUTATION

    product_type.product_attributes.add(product_type_post_reference_attribute)

    attr_value = AttributeValue.objects.create(
        attribute=product_type_post_reference_attribute,
        name=post.title,
        slug=f"{product.pk}_{post.pk}",
        reference_post=post,
    )

    associate_attribute_values_to_instance(
        product, product_type_post_reference_attribute, attr_value
    )

    reference_id = graphene.Node.to_global_id("Post", post.pk)

    variables = {"id": reference_id}
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postDelete"]

    with pytest.raises(attr_value._meta.model.DoesNotExist):
        attr_value.refresh_from_db()
    with pytest.raises(post._meta.model.DoesNotExist):
        post.refresh_from_db()

    assert not data["errors"]


def test_post_delete_removes_reference_to_product_variant(
    product_type_post_reference_attribute,
    staff_api_client,
    post,
    variant,
    permission_manage_posts,
):
    query = POST_DELETE_MUTATION

    product_type = variant.product.product_type
    product_type.variant_attributes.set([product_type_post_reference_attribute])

    attr_value = AttributeValue.objects.create(
        attribute=product_type_post_reference_attribute,
        name=post.title,
        slug=f"{variant.pk}_{post.pk}",
        reference_post=post,
    )

    associate_attribute_values_to_instance(
        variant, product_type_post_reference_attribute, attr_value
    )

    reference_id = graphene.Node.to_global_id("Post", post.pk)

    variables = {"id": reference_id}
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postDelete"]

    with pytest.raises(attr_value._meta.model.DoesNotExist):
        attr_value.refresh_from_db()
    with pytest.raises(post._meta.model.DoesNotExist):
        post.refresh_from_db()

    assert not data["errors"]


def test_post_delete_removes_reference_to_post(
    post_type_post_reference_attribute,
    staff_api_client,
    post_list,
    post_type,
    permission_manage_posts,
):
    post = post_list[0]
    post_ref = post_list[1]

    query = POST_DELETE_MUTATION

    post_type.post_attributes.add(post_type_post_reference_attribute)

    attr_value = AttributeValue.objects.create(
        attribute=post_type_post_reference_attribute,
        name=post.title,
        slug=f"{post.pk}_{post_ref.pk}",
        reference_post=post_ref,
    )

    associate_attribute_values_to_instance(
        post, post_type_post_reference_attribute, attr_value
    )

    reference_id = graphene.Node.to_global_id("Post", post_ref.pk)

    variables = {"id": reference_id}

    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postDelete"]

    with pytest.raises(attr_value._meta.model.DoesNotExist):
        attr_value.refresh_from_db()
    with pytest.raises(post_ref._meta.model.DoesNotExist):
        post_ref.refresh_from_db()

    assert not data["errors"]
