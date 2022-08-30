import graphene
import pytest

from .....attribute.models import AttributeValue
from .....post.models import Post
from ....attribute.utils import associate_attribute_values_to_instance
from ....tests.utils import get_graphql_content

POST_BULK_DELETE_MUTATION = """
    mutation postBulkDelete($ids: [ID!]!) {
        postBulkDelete(ids: $ids) {
            count
            errors {
                code
                field
                message
            }
        }
    }
"""


def test_delete_posts(staff_api_client, post_list, permission_manage_posts):
    query = POST_BULK_DELETE_MUTATION

    variables = {
        "ids": [graphene.Node.to_global_id("Post", post.id) for post in post_list]
    }
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)

    assert content["data"]["postBulkDelete"]["count"] == len(post_list)
    assert not Post.objects.filter(id__in=[post.id for post in post_list]).exists()


def test_post_bulk_delete_with_file_attribute(
    app_api_client,
    post_list,
    post_file_attribute,
    permission_manage_posts,
):
    # given
    app_api_client.app.permissions.add(permission_manage_posts)

    post = post_list[1]
    post_count = len(post_list)
    post_type = post.post_type

    value = post_file_attribute.values.first()
    post_type.post_attributes.add(post_file_attribute)
    associate_attribute_values_to_instance(post, post_file_attribute, value)

    variables = {
        "ids": [graphene.Node.to_global_id("Post", post.pk) for post in post_list]
    }
    # when
    response = app_api_client.post_graphql(POST_BULK_DELETE_MUTATION, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postBulkDelete"]

    assert not data["errors"]
    assert data["count"] == post_count

    with pytest.raises(post._meta.model.DoesNotExist):
        post.refresh_from_db()
    with pytest.raises(value._meta.model.DoesNotExist):
        value.refresh_from_db()

    assert not Post.objects.filter(id__in=[post.id for post in post_list]).exists()


def test_post_delete_removes_reference_to_product(
    product_type_post_reference_attribute,
    post,
    product_type,
    product,
    staff_api_client,
    permission_manage_posts,
):
    query = POST_BULK_DELETE_MUTATION

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

    variables = {"ids": [reference_id]}
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postBulkDelete"]

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
    query = POST_BULK_DELETE_MUTATION

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

    variables = {"ids": [reference_id]}
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postBulkDelete"]

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

    query = POST_BULK_DELETE_MUTATION

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

    variables = {"ids": [reference_id]}

    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    data = content["data"]["postBulkDelete"]

    with pytest.raises(attr_value._meta.model.DoesNotExist):
        attr_value.refresh_from_db()
    with pytest.raises(post_ref._meta.model.DoesNotExist):
        post_ref.refresh_from_db()

    assert not data["errors"]


def test_bulk_delete_post_with_invalid_ids(
    staff_api_client, post_list, permission_manage_posts
):
    query = POST_BULK_DELETE_MUTATION

    variables = {
        "ids": [graphene.Node.to_global_id("Post", post.id) for post in post_list]
    }
    variables["ids"][0] = "invalid_id"
    response = staff_api_client.post_graphql(
        query, variables, permissions=[permission_manage_posts]
    )
    content = get_graphql_content(response)
    errors = content["data"]["postBulkDelete"]["errors"][0]

    assert errors["code"] == "GRAPHQL_ERROR"
