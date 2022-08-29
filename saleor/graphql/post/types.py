from typing import List

import graphene

from ...attribute import models as attribute_models
from ...core.permissions import PostPermissions
from ...post import models
from ..attribute.filters import AttributeFilterInput
from ..attribute.types import Attribute, AttributeCountableConnection, SelectedAttribute
from ..core.connection import (
    CountableConnection,
    create_connection_slice,
    filter_connection_queryset,
)
from ..core.descriptions import ADDED_IN_33, DEPRECATED_IN_3X_FIELD, RICH_CONTENT
from ..core.federation import federated_entity, resolve_federation_references
from ..core.fields import FilterConnectionField, JSONString, PermissionsField
from ..core.types import ModelObjectType, NonNullList
from ..meta.types import ObjectWithMetadata
from ..translations.fields import TranslationField
from ..translations.types import PostTranslation
from .dataloaders import (
    PostAttributesByPostTypeIdLoader,
    PostsByPostTypeIdLoader,
    PostTypeByIdLoader,
    SelectedAttributesByPostIdLoader,
)


@federated_entity("id")
class PostType(ModelObjectType):
    id = graphene.GlobalID(required=True)
    name = graphene.String(required=True)
    slug = graphene.String(required=True)
    attributes = NonNullList(
        Attribute, description="Post attributes of that post type."
    )
    available_attributes = FilterConnectionField(
        AttributeCountableConnection,
        filter=AttributeFilterInput(),
        description="Attributes that can be assigned to the post type.",
        permissions=[
            PostPermissions.MANAGE_POSTS,
        ],
    )
    has_posts = PermissionsField(
        graphene.Boolean,
        description="Whether post type has posts assigned.",
        permissions=[
            PostPermissions.MANAGE_POSTS,
        ],
    )

    class Meta:
        description = (
            "Represents a type of post. It defines what attributes are available to "
            "posts of this type."
        )
        interfaces = [graphene.relay.Node, ObjectWithMetadata]
        model = models.PostType

    @staticmethod
    def get_model():
        return models.PostType

    @staticmethod
    def resolve_attributes(root: models.PostType, info):
        return PostAttributesByPostTypeIdLoader(info.context).load(root.pk)

    @staticmethod
    def resolve_available_attributes(root: models.PostType, info, **kwargs):
        qs = attribute_models.Attribute.objects.get_unassigned_post_type_attributes(
            root.pk
        )
        qs = filter_connection_queryset(qs, kwargs, info.context)
        return create_connection_slice(qs, info, kwargs, AttributeCountableConnection)

    @staticmethod
    def resolve_has_posts(root: models.PostType, info):
        return (
            PostsByPostTypeIdLoader(info.context)
            .load(root.pk)
            .then(lambda posts: bool(posts))
        )

    @staticmethod
    def __resolve_references(roots: List["PostType"], _info):
        return resolve_federation_references(PostType, roots, models.PostType.objects)


class PostTypeCountableConnection(CountableConnection):
    class Meta:
        node = PostType


class Post(ModelObjectType):
    id = graphene.GlobalID(required=True)
    seo_title = graphene.String()
    seo_description = graphene.String()
    title = graphene.String(required=True)
    content = JSONString(description="Content of the post." + RICH_CONTENT)
    publication_date = graphene.Date(
        deprecation_reason=(
            f"{DEPRECATED_IN_3X_FIELD} "
            "Use the `publishedAt` field to fetch the publication date."
        ),
    )
    published_at = graphene.DateTime(
        description="The post publication date." + ADDED_IN_33
    )
    is_published = graphene.Boolean(required=True)
    slug = graphene.String(required=True)
    post_type = graphene.Field(PostType, required=True)
    created = graphene.DateTime(required=True)
    content_json = JSONString(
        description="Content of the post." + RICH_CONTENT,
        deprecation_reason=f"{DEPRECATED_IN_3X_FIELD} Use the `content` field instead.",
        required=True,
    )
    translation = TranslationField(PostTranslation, type_name="post")
    attributes = NonNullList(
        SelectedAttribute,
        required=True,
        description="List of attributes assigned to this product.",
    )

    class Meta:
        description = (
            "A static post that can be manually added by a shop operator through the "
            "dashboard."
        )
        interfaces = [graphene.relay.Node, ObjectWithMetadata]
        model = models.Post

    @staticmethod
    def resolve_publication_date(root: models.Post, _info):
        return root.published_at

    @staticmethod
    def resolve_created(root: models.Post, _info):
        return root.created_at

    @staticmethod
    def resolve_post_type(root: models.Post, info):
        return PostTypeByIdLoader(info.context).load(root.post_type_id)

    @staticmethod
    def resolve_content_json(root: models.Post, _info):
        content = root.content
        return content if content is not None else {}

    @staticmethod
    def resolve_attributes(root: models.Post, info):
        return SelectedAttributesByPostIdLoader(info.context).load(root.id)


class PostCountableConnection(CountableConnection):
    class Meta:
        node = Post
