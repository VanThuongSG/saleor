from unittest.mock import ANY

import graphene

from .....post.error_codes import PostErrorCode
from ....tests.utils import assert_no_permission, get_graphql_content

POST_ASSIGN_ATTR_QUERY = """
    mutation assign($postTypeId: ID!, $attributeIds: [ID!]!) {
      postAttributeAssign(postTypeId: $postTypeId, attributeIds: $attributeIds) {
        errors {
          field
          code
          message
          attributes
        }
        postType {
          id
          attributes {
            id
            visibleInStorefront
            filterableInDashboard
            filterableInStorefront
            availableInGrid
            valueRequired
            storefrontSearchPosition
          }
        }
      }
    }
"""


def test_assign_attributes_to_post_type_by_staff(
    staff_api_client,
    permission_manage_post_types_and_attributes,
    post_type,
    author_post_attribute,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    post_type_attr_count = post_type.post_attributes.count()

    author_post_attr_id = graphene.Node.to_global_id(
        "Attribute", author_post_attribute.pk
    )

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "attributeIds": [author_post_attr_id],
    }

    # when
    response = staff_api_client.post_graphql(POST_ASSIGN_ATTR_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postAttributeAssign"]
    errors = data["errors"]

    assert not errors
    assert len(data["postType"]["attributes"]) == post_type_attr_count + 1
    assert author_post_attr_id in {
        attr["id"] for attr in data["postType"]["attributes"]
    }


def test_assign_attributes_to_post_type_by_app(
    app_api_client,
    permission_manage_post_types_and_attributes,
    post_type,
    author_post_attribute,
):
    # given
    app = app_api_client.app
    app.permissions.add(permission_manage_post_types_and_attributes)

    post_type_attr_count = post_type.post_attributes.count()

    author_post_attr_id = graphene.Node.to_global_id(
        "Attribute", author_post_attribute.pk
    )

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "attributeIds": [author_post_attr_id],
    }

    # when
    response = app_api_client.post_graphql(POST_ASSIGN_ATTR_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postAttributeAssign"]
    errors = data["errors"]

    assert not errors
    assert len(data["postType"]["attributes"]) == post_type_attr_count + 1
    assert author_post_attr_id in {
        attr["id"] for attr in data["postType"]["attributes"]
    }


def test_assign_attributes_to_post_type_by_staff_no_perm(
    staff_api_client,
    permission_manage_post_types_and_attributes,
    post_type,
    author_post_attribute,
):
    # given
    author_post_attr_id = graphene.Node.to_global_id(
        "Attribute", author_post_attribute.pk
    )

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "attributeIds": [author_post_attr_id],
    }

    # when
    response = staff_api_client.post_graphql(POST_ASSIGN_ATTR_QUERY, variables)

    # then
    assert_no_permission(response)


def test_assign_attributes_to_post_type_by_app_no_perm(
    app_api_client,
    permission_manage_post_types_and_attributes,
    post_type,
    author_post_attribute,
):
    # given
    author_post_attr_id = graphene.Node.to_global_id(
        "Attribute", author_post_attribute.pk
    )

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "attributeIds": [author_post_attr_id],
    }

    # when
    response = app_api_client.post_graphql(POST_ASSIGN_ATTR_QUERY, variables)

    # then
    assert_no_permission(response)


def test_assign_attributes_to_post_type_invalid_object_type_as_post_type_id(
    staff_api_client,
    permission_manage_post_types_and_attributes,
    post_type,
    author_post_attribute,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    author_post_attr_id = graphene.Node.to_global_id(
        "Attribute", author_post_attribute.pk
    )

    variables = {
        "postTypeId": graphene.Node.to_global_id("ProductType", post_type.pk),
        "attributeIds": [author_post_attr_id],
    }

    # when
    response = staff_api_client.post_graphql(POST_ASSIGN_ATTR_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postAttributeAssign"]
    errors = data["errors"]

    assert len(errors) == 1
    assert not data["postType"]
    assert errors[0]["field"] == "postTypeId"
    assert errors[0]["code"] == PostErrorCode.GRAPHQL_ERROR.name


def test_assign_attributes_to_post_type_invalid_object_for_attributes(
    staff_api_client,
    permission_manage_post_types_and_attributes,
    post_type,
    author_post_attribute,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    author_post_attr_id = graphene.Node.to_global_id("Post", author_post_attribute.pk)

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "attributeIds": [author_post_attr_id],
    }

    # when
    response = staff_api_client.post_graphql(POST_ASSIGN_ATTR_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postAttributeAssign"]
    errors = data["errors"]

    assert len(errors) == 1
    assert not data["postType"]
    assert errors[0]["field"] == "attributeIds"
    assert errors[0]["code"] == PostErrorCode.GRAPHQL_ERROR.name


def test_assign_attributes_to_post_type_not_post_attribute(
    staff_api_client,
    permission_manage_post_types_and_attributes,
    post_type,
    author_post_attribute,
    color_attribute,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    post_type_attr_count = post_type.post_attributes.count()

    author_post_attr_id = graphene.Node.to_global_id(
        "Attribute", author_post_attribute.pk
    )
    color_attribute_id = graphene.Node.to_global_id("Attribute", color_attribute.pk)

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "attributeIds": [author_post_attr_id, color_attribute_id],
    }

    # when
    response = staff_api_client.post_graphql(POST_ASSIGN_ATTR_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postAttributeAssign"]
    errors = data["errors"]

    assert not data["postType"]
    post_type.refresh_from_db()
    assert post_type.post_attributes.count() == post_type_attr_count
    assert len(errors) == 1
    assert errors[0]["field"] == "attributeIds"
    assert errors[0]["code"] == PostErrorCode.INVALID.name
    assert len(errors[0]["attributes"]) == 1
    assert errors[0]["attributes"] == [color_attribute_id]


def test_assign_attributes_to_post_type_attribute_already_assigned(
    staff_api_client,
    permission_manage_post_types_and_attributes,
    post_type,
    author_post_attribute,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    post_type_attr_count = post_type.post_attributes.count()

    assigned_attr = post_type.post_attributes.first()
    assigned_attr_id = graphene.Node.to_global_id("Attribute", assigned_attr.pk)
    author_post_attr_id = graphene.Node.to_global_id(
        "Attribute", author_post_attribute.pk
    )

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "attributeIds": [author_post_attr_id, assigned_attr_id],
    }

    # when
    response = staff_api_client.post_graphql(POST_ASSIGN_ATTR_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postAttributeAssign"]
    errors = data["errors"]

    assert not data["postType"]
    post_type.refresh_from_db()
    assert post_type.post_attributes.count() == post_type_attr_count
    assert len(errors) == 1
    assert errors[0]["field"] == "attributeIds"
    assert errors[0]["code"] == PostErrorCode.ATTRIBUTE_ALREADY_ASSIGNED.name
    assert len(errors[0]["attributes"]) == 1
    assert errors[0]["attributes"] == [assigned_attr_id]


def test_assign_attributes_to_post_type_multiple_error_returned(
    staff_api_client,
    permission_manage_post_types_and_attributes,
    post_type,
    author_post_attribute,
    color_attribute,
):
    """Ensure that when multiple errors occurred all will br returned."""
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    post_type_attr_count = post_type.post_attributes.count()

    assigned_attr = post_type.post_attributes.first()
    assigned_attr_id = graphene.Node.to_global_id("Attribute", assigned_attr.pk)
    author_post_attr_id = graphene.Node.to_global_id(
        "Attribute", author_post_attribute.pk
    )
    color_attribute_id = graphene.Node.to_global_id("Attribute", color_attribute.pk)

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "attributeIds": [author_post_attr_id, assigned_attr_id, color_attribute_id],
    }

    # when
    response = staff_api_client.post_graphql(POST_ASSIGN_ATTR_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postAttributeAssign"]
    errors = data["errors"]

    assert not data["postType"]
    post_type.refresh_from_db()
    assert post_type.post_attributes.count() == post_type_attr_count
    assert len(errors) == 2
    expected_errors = [
        {
            "field": "attributeIds",
            "code": PostErrorCode.ATTRIBUTE_ALREADY_ASSIGNED.name,
            "attributes": [assigned_attr_id],
            "message": ANY,
        },
        {
            "field": "attributeIds",
            "code": PostErrorCode.INVALID.name,
            "attributes": [color_attribute_id],
            "message": ANY,
        },
    ]
    assert len(errors) == len(expected_errors)
    for error in errors:
        assert error in expected_errors
