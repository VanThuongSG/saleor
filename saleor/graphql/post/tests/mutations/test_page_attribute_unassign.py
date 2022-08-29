import graphene

from ....tests.utils import assert_no_permission, get_graphql_content

POST_UNASSIGN_ATTR_QUERY = """
    mutation PostAttributeUnassign(
        $postTypeId: ID!, $attributeIds: [ID!]!
    ) {
        postAttributeUnassign(
            postTypeId: $postTypeId, attributeIds: $attributeIds
        ) {
            postType {
                id
                attributes {
                    id
                }
            }
            errors {
                field
                code
                message
                attributes
            }
        }
    }
"""


def test_unassign_attributes_from_post_type_by_staff(
    staff_api_client, post_type, permission_manage_post_types_and_attributes
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_post_types_and_attributes)

    attr_count = post_type.post_attributes.count()
    attr_to_unassign = post_type.post_attributes.first()
    attr_to_unassign_id = graphene.Node.to_global_id("Attribute", attr_to_unassign.pk)

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "attributeIds": [attr_to_unassign_id],
    }

    # when
    response = staff_api_client.post_graphql(POST_UNASSIGN_ATTR_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postAttributeUnassign"]
    errors = data["errors"]

    assert not errors
    assert len(data["postType"]["attributes"]) == attr_count - 1
    assert attr_to_unassign_id not in {
        attr["id"] for attr in data["postType"]["attributes"]
    }


def test_unassign_attributes_from_post_type_by_staff_no_perm(
    staff_api_client, post_type
):
    # given
    attr_to_unassign = post_type.post_attributes.first()
    attr_to_unassign_id = graphene.Node.to_global_id("Attribute", attr_to_unassign.pk)

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "attributeIds": [attr_to_unassign_id],
    }

    # when
    response = staff_api_client.post_graphql(POST_UNASSIGN_ATTR_QUERY, variables)

    # then
    assert_no_permission(response)


def test_unassign_attributes_from_post_type_by_app(
    app_api_client, post_type, permission_manage_post_types_and_attributes
):
    # given
    app = app_api_client.app
    app.permissions.add(permission_manage_post_types_and_attributes)

    attr_count = post_type.post_attributes.count()
    attr_to_unassign = post_type.post_attributes.first()
    attr_to_unassign_id = graphene.Node.to_global_id("Attribute", attr_to_unassign.pk)

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "attributeIds": [attr_to_unassign_id],
    }

    # when
    response = app_api_client.post_graphql(POST_UNASSIGN_ATTR_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postAttributeUnassign"]
    errors = data["errors"]

    assert not errors
    assert len(data["postType"]["attributes"]) == attr_count - 1
    assert attr_to_unassign_id not in {
        attr["id"] for attr in data["postType"]["attributes"]
    }


def test_unassign_attributes_from_post_type_by_app_no_perm(app_api_client, post_type):
    # given
    attr_to_unassign = post_type.post_attributes.first()
    attr_to_unassign_id = graphene.Node.to_global_id("Attribute", attr_to_unassign.pk)

    variables = {
        "postTypeId": graphene.Node.to_global_id("PostType", post_type.pk),
        "attributeIds": [attr_to_unassign_id],
    }

    # when
    response = app_api_client.post_graphql(POST_UNASSIGN_ATTR_QUERY, variables)

    # then
    assert_no_permission(response)
