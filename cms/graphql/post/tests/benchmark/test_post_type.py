import graphene
import pytest

from .....post.models import PostType
from ....tests.utils import get_graphql_content


@pytest.mark.django_db
@pytest.mark.count_queries(autouse=False)
def test_query_post_type(
    post_type,
    staff_api_client,
    author_post_attribute,
    permission_manage_posts,
    permission_manage_products,
    count_queries,
):
    query = """
        query PostType($id: ID!, $filters: AttributeFilterInput) {
            postType(id: $id) {
                id
                name
                slug
                hasPosts
                attributes {
                    slug
                    name
                    type
                    inputType
                    choices(first: 10) {
                        edges {
                            node {
                                name
                                slug
                            }
                        }
                    }
                    valueRequired
                    visibleInStorefront
                    filterableInStorefront
                }
                availableAttributes(first: 10, filter: $filters) {
                    edges {
                        node {
                            slug
                            name
                            type
                            inputType
                            choices(first: 10) {
                                edges {
                                    node {
                                        name
                                        slug
                                    }
                                }
                            }
                            valueRequired
                            visibleInStorefront
                            filterableInStorefront
                        }
                    }
                }
            }
        }
    """
    variables = {"id": graphene.Node.to_global_id("PostType", post_type.pk)}
    response = staff_api_client.post_graphql(
        query,
        variables,
        permissions=[permission_manage_products, permission_manage_posts],
    )
    content = get_graphql_content(response)
    data = content["data"]["postType"]
    assert data


@pytest.mark.django_db
@pytest.mark.count_queries(autouse=False)
def test_query_post_types(
    post_type_list,
    staff_api_client,
    author_post_attribute,
    permission_manage_posts,
    permission_manage_products,
    count_queries,
):
    query = """
        query {
            postTypes(first: 10) {
                edges {
                    node {
                        id
                        name
                        slug
                        hasPosts
                        attributes {
                            slug
                            name
                            type
                            inputType
                            choices(first: 10) {
                                edges {
                                    node {
                                        name
                                        slug
                                    }
                                }
                            }
                            valueRequired
                            visibleInStorefront
                            filterableInStorefront
                        }
                        availableAttributes(first: 10) {
                            edges {
                                node {
                                    slug
                                    name
                                    type
                                    inputType
                                    choices(first: 10) {
                                        edges {
                                            node {
                                                name
                                                slug
                                            }
                                        }
                                    }
                                    valueRequired
                                    visibleInStorefront
                                    filterableInStorefront
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    response = staff_api_client.post_graphql(
        query,
        {},
        permissions=[permission_manage_products, permission_manage_posts],
    )
    content = get_graphql_content(response)
    data = content["data"]["postTypes"]
    assert data


@pytest.mark.django_db
@pytest.mark.count_queries(autouse=False)
def test_post_types_for_federation_query_count(
    api_client,
    django_assert_num_queries,
    count_queries,
):
    post_types = PostType.objects.bulk_create(
        [
            PostType(name="type 1", slug="type-1"),
            PostType(name="type 2", slug="type-2"),
            PostType(name="type 3", slug="type-3"),
        ]
    )

    query = """
        query GetAppInFederation($representations: [_Any]) {
            _entities(representations: $representations) {
                __typename
                ... on PostType {
                    id
                    name
                }
            }
        }
    """

    variables = {
        "representations": [
            {
                "__typename": "PostType",
                "id": graphene.Node.to_global_id("PostType", post_types[0].pk),
            },
        ],
    }

    with django_assert_num_queries(1):
        response = api_client.post_graphql(query, variables)
        content = get_graphql_content(response)
        assert len(content["data"]["_entities"]) == 1

    variables = {
        "representations": [
            {
                "__typename": "PostType",
                "id": graphene.Node.to_global_id("PostType", post_type.pk),
            }
            for post_type in post_types
        ],
    }

    with django_assert_num_queries(1):
        response = api_client.post_graphql(query, variables)
        content = get_graphql_content(response)
        assert len(content["data"]["_entities"]) == 3
