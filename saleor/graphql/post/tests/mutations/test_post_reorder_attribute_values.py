import graphene

from .....attribute.models import AttributeValue
from .....attribute.utils import associate_attribute_values_to_instance
from .....post.error_codes import PostErrorCode
from ....tests.utils import get_graphql_content

POST_REORDER_ATTRIBUTE_VALUES_MUTATION = """
    mutation PostReorderAttributeValues(
      $postId: ID!
      $attributeId: ID!
      $moves: [ReorderInput!]!
    ) {
      postReorderAttributeValues(
        postId: $postId
        attributeId: $attributeId
        moves: $moves
      ) {
        post {
          id
          attributes {
            attribute {
                id
                slug
            }
            values {
                id
            }
          }
        }

        errors {
          field
          message
          code
          attributes
          values
        }
      }
    }
"""


def test_sort_post_attribute_values(
    staff_api_client,
    permission_manage_posts,
    post,
    post_type_post_reference_attribute,
):
    staff_api_client.user.user_permissions.add(permission_manage_posts)

    post_type = post.post_type
    post_type.post_attributes.clear()
    post_type.post_attributes.add(post_type_post_reference_attribute)

    post_id = graphene.Node.to_global_id("Post", post.id)
    attribute_id = graphene.Node.to_global_id(
        "Attribute", post_type_post_reference_attribute.id
    )
    attr_values = AttributeValue.objects.bulk_create(
        [
            AttributeValue(
                attribute=post_type_post_reference_attribute,
                slug=f"{post.pk}_1",
                name="test name 1",
            ),
            AttributeValue(
                attribute=post_type_post_reference_attribute,
                slug=f"{post.pk}_2",
                name="test name 2",
            ),
            AttributeValue(
                attribute=post_type_post_reference_attribute,
                slug=f"{post.pk}_3",
                name="test name 3",
            ),
        ]
    )
    associate_attribute_values_to_instance(
        post, post_type_post_reference_attribute, *attr_values
    )

    variables = {
        "postId": post_id,
        "attributeId": attribute_id,
        "moves": [
            {
                "id": graphene.Node.to_global_id("AttributeValue", attr_values[0].pk),
                "sortOrder": +1,
            },
            {
                "id": graphene.Node.to_global_id("AttributeValue", attr_values[2].pk),
                "sortOrder": -2,
            },
        ],
    }

    expected_order = [attr_values[2].pk, attr_values[1].pk, attr_values[0].pk]

    content = get_graphql_content(
        staff_api_client.post_graphql(POST_REORDER_ATTRIBUTE_VALUES_MUTATION, variables)
    )["data"]["postReorderAttributeValues"]
    assert not content["errors"]

    assert content["post"]["id"] == post_id, "Did not return the correct post"

    gql_attribute_values = content["post"]["attributes"][0]["values"]
    assert len(gql_attribute_values) == 3

    for attr, expected_pk in zip(gql_attribute_values, expected_order):
        db_type, value_pk = graphene.Node.from_global_id(attr["id"])
        assert db_type == "AttributeValue"
        assert int(value_pk) == expected_pk


def test_sort_post_attribute_values_invalid_attribute_id(
    staff_api_client,
    permission_manage_posts,
    post,
    post_type_post_reference_attribute,
    color_attribute,
):
    staff_api_client.user.user_permissions.add(permission_manage_posts)

    post_type = post.post_type
    post_type.post_attributes.clear()
    post_type.post_attributes.add(post_type_post_reference_attribute)

    post_id = graphene.Node.to_global_id("Post", post.id)
    attr_values = AttributeValue.objects.bulk_create(
        [
            AttributeValue(
                attribute=post_type_post_reference_attribute,
                slug=f"{post.pk}_1",
                name="test name 1",
            ),
            AttributeValue(
                attribute=post_type_post_reference_attribute,
                slug=f"{post.pk}_2",
                name="test name 2",
            ),
        ]
    )
    associate_attribute_values_to_instance(
        post, post_type_post_reference_attribute, *attr_values
    )

    variables = {
        "postId": post_id,
        "attributeId": graphene.Node.to_global_id("Attribute", color_attribute.pk),
        "moves": [
            {
                "id": graphene.Node.to_global_id("AttributeValue", attr_values[0].pk),
                "sortOrder": +1,
            },
        ],
    }

    content = get_graphql_content(
        staff_api_client.post_graphql(POST_REORDER_ATTRIBUTE_VALUES_MUTATION, variables)
    )["data"]["postReorderAttributeValues"]
    errors = content["errors"]
    assert not content["post"]
    assert len(errors) == 1
    assert errors[0]["code"] == PostErrorCode.NOT_FOUND.name
    assert errors[0]["field"] == "attributeId"


def test_sort_post_attribute_values_invalid_value_id(
    staff_api_client,
    permission_manage_posts,
    post,
    post_type_post_reference_attribute,
    size_post_attribute,
):
    staff_api_client.user.user_permissions.add(permission_manage_posts)

    post_type = post.post_type
    post_type.post_attributes.clear()
    post_type.post_attributes.add(post_type_post_reference_attribute)

    post_id = graphene.Node.to_global_id("Post", post.id)
    attribute_id = graphene.Node.to_global_id(
        "Attribute", post_type_post_reference_attribute.id
    )
    attr_values = AttributeValue.objects.bulk_create(
        [
            AttributeValue(
                attribute=post_type_post_reference_attribute,
                slug=f"{post.pk}_1",
                name="test name 1",
            ),
            AttributeValue(
                attribute=post_type_post_reference_attribute,
                slug=f"{post.pk}_2",
                name="test name 2",
            ),
            AttributeValue(
                attribute=post_type_post_reference_attribute,
                slug=f"{post.pk}_3",
                name="test name 3",
            ),
        ]
    )
    associate_attribute_values_to_instance(
        post, post_type_post_reference_attribute, *attr_values
    )

    invalid_value_id = graphene.Node.to_global_id(
        "AttributeValue", size_post_attribute.values.first().pk
    )

    variables = {
        "postId": post_id,
        "attributeId": attribute_id,
        "moves": [
            {"id": invalid_value_id, "sortOrder": +1},
            {
                "id": graphene.Node.to_global_id("AttributeValue", attr_values[2].pk),
                "sortOrder": -1,
            },
        ],
    }

    content = get_graphql_content(
        staff_api_client.post_graphql(POST_REORDER_ATTRIBUTE_VALUES_MUTATION, variables)
    )["data"]["postReorderAttributeValues"]
    errors = content["errors"]
    assert not content["post"]
    assert len(errors) == 1
    assert errors[0]["code"] == PostErrorCode.NOT_FOUND.name
    assert errors[0]["field"] == "moves"
    assert errors[0]["values"] == [invalid_value_id]
