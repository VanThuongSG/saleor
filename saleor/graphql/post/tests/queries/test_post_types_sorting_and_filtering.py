import graphene
import pytest

from .....post.models import PostType
from ....tests.utils import get_graphql_content

POST_TYPES_QUERY = """
    query PostTypes($filter: PostTypeFilterInput, $sortBy: PostTypeSortingInput) {
        postTypes(first: 10, filter: $filter, sortBy: $sortBy) {
            edges {
                node {
                    id
                }
            }
        }
    }
"""


@pytest.mark.parametrize(
    "search_value, result_items",
    [("test", [0]), ("post", [0, 1, 2]), ("Example post", [1, 2])],
)
def test_filter_post_types(
    search_value, result_items, staff_api_client, post_type_list
):
    # given
    variables = {"filter": {"search": search_value}}

    # when
    response = staff_api_client.post_graphql(POST_TYPES_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypes"]["edges"]

    assert {node["node"]["id"] for node in data} == {
        graphene.Node.to_global_id("PostType", post_type_list[i].pk)
        for i in result_items
    }


@pytest.mark.parametrize(
    "direction, order_direction",
    (("ASC", "name"), ("DESC", "-name")),
)
def test_sort_post_types_by_name(
    direction, order_direction, staff_api_client, post_type_list
):
    # given
    variables = {"sortBy": {"field": "NAME", "direction": direction}}

    # when
    response = staff_api_client.post_graphql(POST_TYPES_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypes"]["edges"]

    assert [node["node"]["id"] for node in data] == [
        graphene.Node.to_global_id("PostType", post_type.pk)
        for post_type in PostType.objects.order_by(order_direction)
    ]


@pytest.mark.parametrize(
    "direction, order_direction",
    (("ASC", "slug"), ("DESC", "-slug")),
)
def test_sort_post_types_by_slug(
    direction, order_direction, staff_api_client, post_type_list
):
    # given
    variables = {"sortBy": {"field": "SLUG", "direction": direction}}

    # when
    response = staff_api_client.post_graphql(POST_TYPES_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypes"]["edges"]

    assert [node["node"]["id"] for node in data] == [
        graphene.Node.to_global_id("PostType", post_type.pk)
        for post_type in PostType.objects.order_by(order_direction)
    ]


@pytest.mark.parametrize(
    "direction, result_items",
    (("ASC", [1, 2]), ("DESC", [2, 1])),
)
def test_filter_and_sort_by_slug_post_types(
    direction, result_items, staff_api_client, post_type_list
):
    # given
    variables = {
        "filter": {"search": "Example"},
        "sortBy": {"field": "SLUG", "direction": direction},
    }

    # when
    response = staff_api_client.post_graphql(POST_TYPES_QUERY, variables)

    # then
    content = get_graphql_content(response)
    data = content["data"]["postTypes"]["edges"]

    assert [node["node"]["id"] for node in data] == [
        graphene.Node.to_global_id("PostType", post_type_list[i].pk)
        for i in result_items
    ]
