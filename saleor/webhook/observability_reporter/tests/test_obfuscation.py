import pytest
from graphql import GraphQLError

from ..obfuscation import (
    MASK,
    anonymize_gql_operation_response,
    hide_sensitive_headers,
    validate_sensitive_fields_map,
)
from .conftest import GqlOperationFactoryType, schema


@pytest.mark.parametrize(
    "headers,sensitive,expected",
    [
        (
            {"header1": "text", "header2": "text"},
            ("AUTHORIZATION", "AUTHORIZATION_BEARER"),
            {"header1": "text", "header2": "text"},
        ),
        (
            {"header1": "text", "authorization": "secret"},
            ("AUTHORIZATION", "AUTHORIZATION_BEARER"),
            {"header1": "text", "authorization": MASK},
        ),
        (
            {"HEADER1": "text", "authorization-bearer": "secret"},
            ("AUTHORIZATION", "AUTHORIZATION_BEARER"),
            {"HEADER1": "text", "authorization-bearer": MASK},
        ),
    ],
)
def test_hide_sensitive_headers(headers, sensitive, expected):
    assert hide_sensitive_headers(headers, sensitive_headers=sensitive) == expected


def test_anonymize_gql_operation_response(
    gql_operation_factory: GqlOperationFactoryType,
):
    query = "query FirstQuery { shop { name } }"
    result = {"data": "result"}
    sensitive_fields = {"Shop": {"name"}}
    operation_result = gql_operation_factory(query, result=result)

    anonymize_gql_operation_response(operation_result, sensitive_fields)

    assert operation_result.result["data"] == MASK


def test_anonymize_gql_operation_with_mutation_in_query(
    gql_operation_factory: GqlOperationFactoryType,
):
    query = """
    mutation tokenRefresh($token: String){
        tokenRefresh(refreshToken: $token){
            token
        }
    }"""
    result = {"data": {"tokenRefresh": {"token": "SECRET TOKEN"}}}
    sensitive_fields = {"RefreshToken": {"token"}}
    operation_result = gql_operation_factory(query, result=result)

    anonymize_gql_operation_response(operation_result, sensitive_fields)

    assert operation_result.result["data"] == MASK


def test_anonymize_gql_operation_with_subscription_in_query(
    gql_operation_factory: GqlOperationFactoryType,
):
    query = """
    subscription{
      event{
        ...on ProductUpdated{
          product{
            id
            name
          }
        }
      }
    }
    """
    result = {"data": "secret data"}
    sensitive_fields = {"Product": {"name"}}
    operation_result = gql_operation_factory(query, result=result)

    anonymize_gql_operation_response(operation_result, sensitive_fields)

    assert operation_result.result["data"] == MASK


def test_anonymize_gql_operation_response_with_empty_sensitive_fields_map(
    gql_operation_factory: GqlOperationFactoryType,
):
    query = "query FirstQuery { shop { name } }"
    result = {"data": "result"}
    operation_result = gql_operation_factory(query, result=result)

    anonymize_gql_operation_response(operation_result, {})

    assert operation_result.result == result


def test_anonymize_gql_operation_response_with_fragment_spread(
    gql_operation_factory: GqlOperationFactoryType,
):
    query = """
    fragment ProductFragment on Product {
      id
      name
    }
    query products($first: Int){
      products(channel: "channel-pln", first:$first){
        edges{
          node{
            ... ProductFragment
            variants {
                variantName: name
            }
          }
        }
      }
    }"""
    result = {"data": "result"}
    sensitive_fields = {"Product": {"name"}}
    operation_result = gql_operation_factory(query, result=result)

    anonymize_gql_operation_response(operation_result, sensitive_fields)

    assert operation_result.result["data"] == MASK


@pytest.mark.parametrize(
    "sensitive_fields",
    [
        {"NonExistingType": {}},
        {"Product": {"nonExistingField"}},
        {"Node": {"id"}},
    ],
)
def test_validate_sensitive_fields_map(sensitive_fields):
    with pytest.raises(GraphQLError):
        validate_sensitive_fields_map(sensitive_fields, schema)