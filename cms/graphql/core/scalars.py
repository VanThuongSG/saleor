import decimal

import graphene
from graphql.error import GraphQLError
from graphql.language import ast
from measurement.measures import Weight


class Decimal(graphene.Float):
    """Custom Decimal implementation.

    Returns Decimal as a float in the API,
    parses float to the Decimal on the way back.
    """

    @staticmethod
    def parse_literal(node):
        try:
            return decimal.Decimal(node.value)
        except decimal.DecimalException:
            return None

    @staticmethod
    def parse_value(value):
        try:
            # Converting the float to str before parsing it to Decimal is
            # necessary to keep the decimal places as typed
            value = str(value)
            return decimal.Decimal(value)
        except decimal.DecimalException:
            return None


class PositiveDecimal(Decimal):
    """Positive Decimal scalar implementation.

    Should be used in places where value must be positive.
    """

    @staticmethod
    def parse_value(value):
        value = super(PositiveDecimal, PositiveDecimal).parse_value(value)
        if value and value < 0:
            raise GraphQLError(
                f"Value cannot be lower than 0. Unsupported value: {value}"
            )
        return value


class UUID(graphene.UUID):
    @staticmethod
    def serialize(uuid):
        return super(UUID, UUID).serialize(uuid)

    @staticmethod
    def parse_literal(node):
        try:
            return super(UUID, UUID).parse_literal(node)
        except ValueError as e:
            raise GraphQLError(str(e))

    @staticmethod
    def parse_value(value):
        try:
            return super(UUID, UUID).parse_value(value)
        except ValueError as e:
            raise GraphQLError(str(e))
