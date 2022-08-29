import graphene

from .....attribute.models import AttributeValue
from .....attribute.utils import associate_attribute_values_to_instance
from .....tests.utils import dummy_editorjs
from ....tests.utils import get_graphql_content, get_graphql_content_from_response

POST_QUERY = """
    query PostQuery($id: ID, $slug: String) {
        post(id: $id, slug: $slug) {
            id
            title
            slug
            postType {
                id
            }
            content
            contentJson
            attributes {
                attribute {
                    slug
                }
                values {
                    id
                    slug
                }
            }
        }
    }
"""


def test_query_published_post(user_api_client, post):
    post.is_published = True
    post.save()

    post_type = post.post_type

    assert post.attributes.count() == 1
    post_attr_assigned = post.attributes.first()
    post_attr = post_attr_assigned.attribute

    assert post_attr_assigned.values.count() == 1
    post_attr_value = post_attr_assigned.values.first()

    # query by ID
    variables = {"id": graphene.Node.to_global_id("Post", post.id)}
    response = user_api_client.post_graphql(POST_QUERY, variables)
    content = get_graphql_content(response)
    post_data = content["data"]["post"]
    assert (
        post_data["content"]
        == post_data["contentJson"]
        == dummy_editorjs("Test content.", True)
    )
    assert post_data["title"] == post.title
    assert post_data["slug"] == post.slug
    assert post_data["postType"]["id"] == graphene.Node.to_global_id(
        "PostType", post.post_type.pk
    )

    expected_attributes = []
    for attr in post_type.post_attributes.all():
        values = (
            [
                {
                    "slug": post_attr_value.slug,
                    "id": graphene.Node.to_global_id(
                        "AttributeValue", post_attr_value.pk
                    ),
                }
            ]
            if attr.slug == post_attr.slug
            else []
        )
        expected_attributes.append({"attribute": {"slug": attr.slug}, "values": values})

    for attr_data in post_data["attributes"]:
        assert attr_data in expected_attributes

    # query by slug
    variables = {"slug": post.slug}
    response = user_api_client.post_graphql(POST_QUERY, variables)
    content = get_graphql_content(response)
    assert content["data"]["post"]["id"] == graphene.Node.to_global_id("Post", post.id)


def test_customer_query_unpublished_post(user_api_client, post):
    post.is_published = False
    post.save()

    # query by ID
    variables = {"id": graphene.Node.to_global_id("Post", post.id)}
    response = user_api_client.post_graphql(POST_QUERY, variables)
    content = get_graphql_content(response)
    assert content["data"]["post"] is None

    # query by slug
    variables = {"slug": post.slug}
    response = user_api_client.post_graphql(POST_QUERY, variables)
    content = get_graphql_content(response)
    assert content["data"]["post"] is None


def test_staff_query_unpublished_post_by_id(
    staff_api_client, post, permission_manage_posts
):
    post.is_published = False
    post.save()

    # query by ID
    variables = {"id": graphene.Node.to_global_id("Post", post.id)}
    response = staff_api_client.post_graphql(
        POST_QUERY,
        variables,
        permissions=[permission_manage_posts],
        check_no_permissions=False,
    )
    content = get_graphql_content(response)
    assert content["data"]["post"]["id"] == variables["id"]


def test_staff_query_unpublished_post_by_id_without_required_permission(
    staff_api_client,
    post,
):
    post.is_published = False
    post.save()

    # query by ID
    variables = {"id": graphene.Node.to_global_id("Post", post.id)}
    response = staff_api_client.post_graphql(POST_QUERY, variables)
    content = get_graphql_content(response)
    assert content["data"]["post"] is None


def test_app_query_unpublished_post_by_id(
    app_api_client, post, permission_manage_posts
):
    # given
    post.is_published = False
    post.save()

    app_api_client.app.permissions.add(permission_manage_posts)

    variables = {"id": graphene.Node.to_global_id("Post", post.id)}

    # when
    response = app_api_client.post_graphql(
        POST_QUERY,
        variables,
    )

    # then
    content = get_graphql_content(response)
    assert content["data"]["post"]["id"] == variables["id"]


def test_app_query_unpublished_post_by_id_without_required_permission(
    app_api_client,
    post,
):
    # given
    post.is_published = False
    post.save()

    variables = {"id": graphene.Node.to_global_id("Post", post.id)}

    # when
    response = app_api_client.post_graphql(POST_QUERY, variables)

    # then
    content = get_graphql_content(response)
    assert content["data"]["post"] is None


def test_app_query_unpublished_post_by_slug(
    app_api_client, post, permission_manage_posts
):
    # given
    post.is_published = False
    post.save()

    app_api_client.app.permissions.add(permission_manage_posts)

    variables = {"slug": post.slug}

    # when
    response = app_api_client.post_graphql(
        POST_QUERY,
        variables,
    )

    # then
    content = get_graphql_content(response)
    assert content["data"]["post"]["id"] == graphene.Node.to_global_id("Post", post.id)


def test_app_query_unpublished_post_by_slug_without_required_permission(
    app_api_client,
    post,
):
    # given
    post.is_published = False
    post.save()

    # when
    variables = {"slug": post.slug}

    # then
    response = app_api_client.post_graphql(POST_QUERY, variables)
    content = get_graphql_content(response)
    assert content["data"]["post"] is None


def test_staff_query_unpublished_post_by_slug(
    staff_api_client, post, permission_manage_posts
):
    post.is_published = False
    post.save()

    # query by slug
    variables = {"slug": post.slug}
    response = staff_api_client.post_graphql(
        POST_QUERY,
        variables,
        permissions=[permission_manage_posts],
        check_no_permissions=False,
    )
    content = get_graphql_content(response)
    assert content["data"]["post"]["id"] == graphene.Node.to_global_id("Post", post.id)


def test_staff_query_unpublished_post_by_slug_without_required_permission(
    staff_api_client,
    post,
):
    post.is_published = False
    post.save()

    # query by slug
    variables = {"slug": post.slug}
    response = staff_api_client.post_graphql(POST_QUERY, variables)
    content = get_graphql_content(response)
    assert content["data"]["post"] is None


def test_staff_query_post_by_invalid_id(staff_api_client, post):
    id = "bh/"
    variables = {"id": id}
    response = staff_api_client.post_graphql(POST_QUERY, variables)
    content = get_graphql_content_from_response(response)
    assert len(content["errors"]) == 1
    assert content["errors"][0]["message"] == f"Couldn't resolve id: {id}."
    assert content["data"]["post"] is None


def test_staff_query_post_with_invalid_object_type(staff_api_client, post):
    variables = {"id": graphene.Node.to_global_id("Order", post.id)}
    response = staff_api_client.post_graphql(POST_QUERY, variables)
    content = get_graphql_content(response)
    assert content["data"]["post"] is None


def test_get_post_with_sorted_attribute_values(
    staff_api_client,
    post,
    product_list,
    post_type_product_reference_attribute,
    permission_manage_posts,
):
    # given
    post_type = post.post_type
    post_type.post_attributes.set([post_type_product_reference_attribute])

    attr_value_1 = AttributeValue.objects.create(
        attribute=post_type_product_reference_attribute,
        name=product_list[0].name,
        slug=f"{post.pk}_{product_list[0].pk}",
    )
    attr_value_2 = AttributeValue.objects.create(
        attribute=post_type_product_reference_attribute,
        name=product_list[1].name,
        slug=f"{post.pk}_{product_list[1].pk}",
    )
    attr_value_3 = AttributeValue.objects.create(
        attribute=post_type_product_reference_attribute,
        name=product_list[2].name,
        slug=f"{post.pk}_{product_list[2].pk}",
    )

    attr_values = [attr_value_2, attr_value_1, attr_value_3]
    associate_attribute_values_to_instance(
        post, post_type_product_reference_attribute, *attr_values
    )

    post_id = graphene.Node.to_global_id("Post", post.id)
    variables = {"id": post_id}
    staff_api_client.user.user_permissions.add(permission_manage_posts)

    # when
    response = staff_api_client.post_graphql(POST_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["post"]
    assert len(data["attributes"]) == 1
    values = data["attributes"][0]["values"]
    assert len(values) == 3
    assert [value["id"] for value in values] == [
        graphene.Node.to_global_id("AttributeValue", val.pk) for val in attr_values
    ]
