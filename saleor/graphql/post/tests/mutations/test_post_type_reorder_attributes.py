import graphene

from .....post.error_codes import PostErrorCode
from .....post.models import PostType
from ....tests.utils import assert_no_permission, get_graphql_content

POST_TYPE_REORDER_ATTRIBUTES_MUTATION = """
    mutation PostTypeReorderAttributes(
        $postTypeId: ID!
        $moves: [ReorderInput!]!
    ) {
        postTypeReorderAttributes(
            postTypeId: $postTypeId
            moves: $moves
        ) {
            postType {
                id
                attributes {
                    id
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


def test_reorder_post_type_attributes_by_staff(
    staff_api_client,
    permission_manage_post_types_and_attributes,
    post_type_attribute_list,
):
    # given
    staff_api_client.user.user_permissions.add(
        permission_manage_post_types_and_attributes
    )

    attributes = post_type_attribute_list
    assert len(attributes) == 3

    post_type = PostType.objects.create(name="Test post type", slug="test-post-type")
    post_type.post_attributes.set(attributes)

    sorted_attributes = list(post_type.post_attributes.order_by())

    assert len(sorted_attributes) == 3

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "moves": [
            {
                "id": graphene.Node.to_global_id("Attribute", sorted_attributes[2].pk),
                "sortOrder": -2,
            },
            {
                "id": graphene.Node.to_global_id("Attribute", sorted_attributes[0].pk),
                "sortOrder": 1,
            },
        ],
    }

    # when
    response = staff_api_client.post_graphql(
        POST_TYPE_REORDER_ATTRIBUTES_MUTATION, variables
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeReorderAttributes"]
    errors = data["errors"]
    post_type_data = data["postType"]

    assert not errors
    assert len(post_type_data["attributes"]) == len(sorted_attributes)

    expected_order = [
        sorted_attributes[2].pk,
        sorted_attributes[1].pk,
        sorted_attributes[0].pk,
    ]

    for attr, expected_pk in zip(post_type_data["attributes"], expected_order):
        gql_type, gql_attr_id = graphene.Node.from_global_id(attr["id"])
        assert gql_type == "Attribute"
        assert int(gql_attr_id) == expected_pk


def test_reorder_post_type_attributes_by_staff_no_perm(
    staff_api_client, post_type_attribute_list
):
    # given
    attributes = post_type_attribute_list
    assert len(attributes) == 3

    post_type = PostType.objects.create(name="Test post type", slug="test-post-type")
    post_type.post_attributes.set(attributes)

    sorted_attributes = list(post_type.post_attributes.order_by())

    assert len(sorted_attributes) == 3

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "moves": [
            {
                "id": graphene.Node.to_global_id("Attribute", attributes[0].pk),
                "sortOrder": 1,
            },
            {
                "id": graphene.Node.to_global_id("Attribute", attributes[2].pk),
                "sortOrder": -1,
            },
        ],
    }

    # when
    response = staff_api_client.post_graphql(
        POST_TYPE_REORDER_ATTRIBUTES_MUTATION, variables
    )

    # then
    assert_no_permission(response)


def test_reorder_post_type_attributes_by_app(
    app_api_client,
    permission_manage_post_types_and_attributes,
    post_type_attribute_list,
):
    # given
    app_api_client.app.permissions.add(permission_manage_post_types_and_attributes)

    attributes = post_type_attribute_list
    assert len(attributes) == 3

    post_type = PostType.objects.create(name="Test post type", slug="test-post-type")
    post_type.post_attributes.set(attributes)

    sorted_attributes = list(post_type.post_attributes.order_by())

    assert len(sorted_attributes) == 3

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "moves": [
            {
                "id": graphene.Node.to_global_id("Attribute", sorted_attributes[2].pk),
                "sortOrder": -2,
            },
            {
                "id": graphene.Node.to_global_id("Attribute", sorted_attributes[0].pk),
                "sortOrder": 1,
            },
        ],
    }

    # when
    response = app_api_client.post_graphql(
        POST_TYPE_REORDER_ATTRIBUTES_MUTATION, variables
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeReorderAttributes"]
    errors = data["errors"]
    post_type_data = data["postType"]

    assert not errors
    assert len(post_type_data["attributes"]) == len(sorted_attributes)

    expected_order = [
        sorted_attributes[2].pk,
        sorted_attributes[1].pk,
        sorted_attributes[0].pk,
    ]

    for attr, expected_pk in zip(post_type_data["attributes"], expected_order):
        gql_type, gql_attr_id = graphene.Node.from_global_id(attr["id"])
        assert gql_type == "Attribute"
        assert int(gql_attr_id) == expected_pk


def test_reorder_post_type_attributes_by_app_no_perm(
    app_api_client, post_type_attribute_list
):
    # given
    attributes = post_type_attribute_list
    assert len(attributes) == 3

    post_type = PostType.objects.create(name="Test post type", slug="test-post-type")
    post_type.post_attributes.set(attributes)

    sorted_attributes = list(post_type.post_attributes.order_by())

    assert len(sorted_attributes) == 3

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "moves": [
            {
                "id": graphene.Node.to_global_id("Attribute", attributes[2].pk),
                "sortOrder": -2,
            },
            {
                "id": graphene.Node.to_global_id("Attribute", attributes[0].pk),
                "sortOrder": 1,
            },
        ],
    }

    # when
    response = app_api_client.post_graphql(
        POST_TYPE_REORDER_ATTRIBUTES_MUTATION, variables
    )

    # then
    assert_no_permission(response)


def test_reorder_post_type_attributes_invalid_post_type(
    staff_api_client, permission_manage_post_types_and_attributes, post_type
):
    # given
    staff_api_client.user.user_permissions.add(
        permission_manage_post_types_and_attributes
    )

    attribute = post_type.post_attributes.first()

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", -1),
        "moves": [
            {
                "id": graphene.Node.to_global_id("Attribute", attribute.pk),
                "sortOrder": 1,
            },
        ],
    }

    # when
    response = staff_api_client.post_graphql(
        POST_TYPE_REORDER_ATTRIBUTES_MUTATION, variables
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeReorderAttributes"]
    errors = data["errors"]
    post_type_data = data["postType"]

    assert not post_type_data
    assert len(errors) == 1
    assert errors[0]["field"] == "postTypeId"
    assert errors[0]["code"] == PostErrorCode.NOT_FOUND.name


def test_reorder_post_type_attributes_invalid_attribute_id(
    staff_api_client,
    permission_manage_post_types_and_attributes,
    post_type,
    color_attribute,
    size_attribute,
):
    # given
    staff_api_client.user.user_permissions.add(
        permission_manage_post_types_and_attributes
    )

    post_type_attribute = post_type.post_attributes.first()
    color_attribute_id = graphene.Node.to_global_id("Attribute", color_attribute.pk)
    size_attribute_id = graphene.Node.to_global_id("Attribute", size_attribute.pk)

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "moves": [
            {"id": color_attribute_id, "sortOrder": 1},
            {
                "id": graphene.Node.to_global_id("Attribute", post_type_attribute.pk),
                "sortOrder": 1,
            },
            {"id": size_attribute_id, "sortOrder": 1},
        ],
    }

    # when
    response = staff_api_client.post_graphql(
        POST_TYPE_REORDER_ATTRIBUTES_MUTATION, variables
    )

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypeReorderAttributes"]
    errors = data["errors"]
    post_type_data = data["postType"]

    assert not post_type_data
    assert len(errors) == 1
    assert errors[0]["field"] == "moves"
    assert errors[0]["code"] == PostErrorCode.NOT_FOUND.name
    assert set(errors[0]["attributes"]) == {color_attribute_id, size_attribute_id}
