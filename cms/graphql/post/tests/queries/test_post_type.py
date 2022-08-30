import graphene

from ....tests.utils import (
    assert_no_permission,
    get_graphql_content,
    get_graphql_content_from_response,
)

POST_TYPE_QUERY = """
    query PostType($id: ID!, $filters: AttributeFilterInput) {
        postType(id: $id) {
            id
            name
            slug
            hasPosts
            attributes {
                slug
            }
            availableAttributes(first: 10, filter: $filters) {
                edges {
                    node {
                        slug
                    }
                }
            }
        }
    }
"""


def test_post_type_query_by_staff(
    staff_api_client,
    post_type,
    author_post_attribute,
    permission_manage_posts,
    color_attribute,
    post,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_posts)

    variables = {"id": graphene.Node.to_global_id("PostType", post_type.pk)}

    # when
    response = staff_api_client.post_graphql(POST_TYPE_QUERY, variables)

    # then
    content = get_graphql_content(response)
    post_type_data = content["data"]["postType"]

    assert post_type_data["slug"] == post_type.slug
    assert post_type_data["name"] == post_type.name
    assert {attr["slug"] for attr in post_type_data["attributes"]} == {
        attr.slug for attr in post_type.post_attributes.all()
    }
    assert post_type_data["hasPosts"] is True
    available_attributes = post_type_data["availableAttributes"]["edges"]
    assert len(available_attributes) == 1
    assert available_attributes[0]["node"]["slug"] == author_post_attribute.slug


def test_post_type_query_by_staff_no_perm(
    staff_api_client, post_type, author_post_attribute
):
    # given
    variables = {"id": graphene.Node.to_global_id("PostType", post_type.pk)}

    # when
    response = staff_api_client.post_graphql(POST_TYPE_QUERY, variables)

    # then
    assert_no_permission(response)


def test_post_type_query_by_app(
    app_api_client,
    post_type,
    author_post_attribute,
    permission_manage_posts,
    color_attribute,
):
    # given
    staff_user = app_api_client.app
    staff_user.permissions.add(permission_manage_posts)

    variables = {"id": graphene.Node.to_global_id("PostType", post_type.pk)}

    # when
    response = app_api_client.post_graphql(POST_TYPE_QUERY, variables)

    # then
    content = get_graphql_content(response)
    post_type_data = content["data"]["postType"]

    assert post_type_data["slug"] == post_type.slug
    assert post_type_data["name"] == post_type.name
    assert {attr["slug"] for attr in post_type_data["attributes"]} == {
        attr.slug for attr in post_type.post_attributes.all()
    }
    available_attributes = post_type_data["availableAttributes"]["edges"]
    assert len(available_attributes) == 1
    assert available_attributes[0]["node"]["slug"] == author_post_attribute.slug


def test_post_type_query_by_app_no_perm(
    app_api_client,
    post_type,
    author_post_attribute,
    permission_manage_post_types_and_attributes,
):
    # given
    variables = {"id": graphene.Node.to_global_id("PostType", post_type.pk)}

    # when
    response = app_api_client.post_graphql(POST_TYPE_QUERY, variables)

    # then
    assert_no_permission(response)


def test_staff_query_post_type_by_invalid_id(staff_api_client, post_type):
    id = "bh/"
    variables = {"id": id}
    response = staff_api_client.post_graphql(POST_TYPE_QUERY, variables)
    content = get_graphql_content_from_response(response)
    assert len(content["errors"]) == 1
    assert content["errors"][0]["message"] == f"Couldn't resolve id: {id}."
    assert content["data"]["postType"] is None


def test_staff_query_post_type_with_invalid_object_type(staff_api_client, post_type):
    variables = {"id": graphene.Node.to_global_id("Order", post_type.pk)}
    response = staff_api_client.post_graphql(POST_TYPE_QUERY, variables)
    content = get_graphql_content(response)
    assert content["data"]["postType"] is None


def test_post_type_query_filter_unassigned_attributes(
    staff_api_client,
    post_type,
    permission_manage_posts,
    post_type_attribute_list,
    color_attribute,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_posts)

    expected_attribute = post_type_attribute_list[0]

    variables = {
        "id": graphene.Node.to_global_id("PostType", post_type.pk),
        "filters": {"search": expected_attribute.name},
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPE_QUERY, variables)

    # then
    content = get_graphql_content(response)
    post_type_data = content["data"]["postType"]

    assert post_type_data["slug"] == post_type.slug
    assert {attr["slug"] for attr in post_type_data["attributes"]} == {
        attr.slug for attr in post_type.post_attributes.all()
    }
    available_attributes = post_type_data["availableAttributes"]["edges"]
    assert len(available_attributes) == 1
    assert available_attributes[0]["node"]["slug"] == expected_attribute.slug


def test_post_type_query_no_posts(
    staff_api_client,
    post_type,
    author_post_attribute,
    permission_manage_posts,
    color_attribute,
):
    # given
    staff_user = staff_api_client.user
    staff_user.user_permissions.add(permission_manage_posts)

    variables = {"id": graphene.Node.to_global_id("PostType", post_type.pk)}

    # when
    response = staff_api_client.post_graphql(POST_TYPE_QUERY, variables)

    # then
    content = get_graphql_content(response)
    post_type_data = content["data"]["postType"]

    assert post_type_data["slug"] == post_type.slug
    assert post_type_data["name"] == post_type.name
    assert {attr["slug"] for attr in post_type_data["attributes"]} == {
        attr.slug for attr in post_type.post_attributes.all()
    }
    assert post_type_data["hasPosts"] is False
    available_attributes = post_type_data["availableAttributes"]["edges"]
    assert len(available_attributes) == 1
    assert available_attributes[0]["node"]["slug"] == author_post_attribute.slug


def test_query_post_types_for_federation(api_client, post_type):
    post_type_id = graphene.Node.to_global_id("PostType", post_type.pk)
    variables = {
        "representations": [
            {
                "__typename": "PostType",
                "id": post_type_id,
            },
        ],
    }
    query = """
      query GetPostTypeInFederation($representations: [_Any]) {
        _entities(representations: $representations) {
          __typename
          ... on PostType {
            id
            name
          }
        }
      }
    """

    response = api_client.post_graphql(query, variables)
    content = get_graphql_content(response)
    assert content["data"]["_entities"] == [
        {
            "__typename": "PostType",
            "id": post_type_id,
            "name": post_type.name,
        }
    ]
