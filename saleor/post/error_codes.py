from enum import Enum


class PostErrorCode(Enum):
    GRAPHQL_ERROR = "graphql_error"
    INVALID = "invalid"
    NOT_FOUND = "not_found"
    REQUIRED = "required"
    UNIQUE = "unique"
    DUPLICATED_INPUT_ITEM = "duplicated_input_item"
    ATTRIBUTE_ALREADY_ASSIGNED = "attribute_already_assigned"
    UNSUPPORTED_MEDIA_PROVIDER = "unsupported_media_provider"
    MEDIA_ALREADY_ASSIGNED = "media_already_assigned"
    NOT_POSTS_IMAGE = "not_posts_image"
