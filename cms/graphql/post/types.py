from typing import List

import graphene
from graphene import relay

from ...core.permissions import (
    PostPermissions,
    has_one_of_permissions,
)
from ...core.tracing import traced_resolver
from ...post import models
from ...post.models import ALL_POSTS_PERMISSIONS
from ...thumbnail.utils import get_image_or_proxy_url, get_thumbnail_size
from ..core.connection import (
    CountableConnection,
    create_connection_slice,
)
from ..core.descriptions import ADDED_IN_33, DEPRECATED_IN_3X_FIELD, RICH_CONTENT
from ..core.federation import federated_entity, resolve_federation_references
from ..core.fields import (
    ConnectionField,
    FilterConnectionField,
    JSONString,
    PermissionsField,
)
from ..core.types import (
    Image,
    ModelObjectType,
    NonNullList,
    ThumbnailField,
)
from ..core.utils import from_global_id_or_error
from ..meta.types import ObjectWithMetadata
from ..translations.fields import TranslationField
from ..translations.types import PostTranslation
from ..utils import get_user_or_app_from_context
from .dataloaders import (
    CategoryByIdLoader,
    CategoryChildrenByCategoryIdLoader,
    ImagesByPostIdLoader,
    PostsByPostTypeIdLoader,
    PostTypeByIdLoader,
    MediaByPostIdLoader,
    ThumbnailByCategoryIdSizeAndFormatLoader,
    ThumbnailByPostMediaIdSizeAndFormatLoader,
)
from .enums import PostMediaType

@federated_entity("id")
class PostType(ModelObjectType):
    id = graphene.GlobalID(required=True)
    name = graphene.String(required=True)
    slug = graphene.String(required=True)    
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
    category = graphene.Field(lambda: Category)
    created = graphene.DateTime(required=True)
    content_json = JSONString(
        description="Content of the post." + RICH_CONTENT,
        deprecation_reason=f"{DEPRECATED_IN_3X_FIELD} Use the `content` field instead.",
        required=True,
    )
    external_url = graphene.String()
    translation = TranslationField(PostTranslation, type_name="post")    
    thumbnail = ThumbnailField()
    media_by_id = graphene.Field(
        lambda: PostMedia,
        id=graphene.Argument(graphene.ID, description="ID of a post media."),
        description="Get a single post media by ID.",
    )
    image_by_id = graphene.Field(
        lambda: PostMedia,
        id=graphene.Argument(graphene.ID, description="ID of a post image."),
        description="Get a single post image by ID.",
        deprecation_reason=(
            f"{DEPRECATED_IN_3X_FIELD} Use the `mediaById` field instead."
        ),
    )
    media = NonNullList(
        lambda: PostMedia,
        description="List of media for the post.",
    )
    images = NonNullList(
        lambda: PostMedia,
        description="List of images for the post.",
        deprecation_reason=f"{DEPRECATED_IN_3X_FIELD} Use the `media` field instead.",
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
    @traced_resolver
    def resolve_thumbnail(
        root: models.Post, info, *, size=256, format=None
    ):
        format = format.lower() if format else None
        size = get_thumbnail_size(size)

        def return_first_thumbnail(post_media):
            if not post_media:
                return None

            image = post_media[0]
            oembed_data = image.oembed_data

            if oembed_data.get("thumbnail_url"):
                return Image(alt=oembed_data["title"], url=oembed_data["thumbnail_url"])

            def _resolve_url(thumbnail):
                url = get_image_or_proxy_url(
                    thumbnail, image.id, "PostMedia", size, format
                )
                return Image(alt=image.alt, url=info.context.build_absolute_uri(url))

            return (
                ThumbnailByPostMediaIdSizeAndFormatLoader(info.context)
                .load((image.id, size, format))
                .then(_resolve_url)
            )

        return (
            MediaByPostIdLoader(info.context)
            .load(root.id)
            .then(return_first_thumbnail)
        )
    
    @staticmethod
    def resolve_media_by_id(root: models.Post, _info, *, id):
        _type, pk = from_global_id_or_error(id, PostMedia)
        return root.media.filter(pk=pk).first()

    @staticmethod
    def resolve_image_by_id(root: models.Post, _info, *, id):
        _type, pk = from_global_id_or_error(id, PostImage)
        return root.media.filter(pk=pk).first()

    @staticmethod
    def resolve_media(root: models.Post, info):
        return MediaByPostIdLoader(info.context).load(root.id)

    @staticmethod
    def resolve_images(root: models.Post, info):
        return ImagesByPostIdLoader(info.context).load(root.id)


class PostCountableConnection(CountableConnection):
    class Meta:
        node = Post


@federated_entity("id")
class PostMedia(ModelObjectType):
    id = graphene.GlobalID(required=True)
    sort_order = graphene.Int()
    alt = graphene.String(required=True)
    type = PostMediaType(required=True)
    oembed_data = JSONString(required=True)
    url = ThumbnailField(graphene.String, required=True)

    class Meta:
        description = "Represents a post media."
        interfaces = [graphene.relay.Node]
        model = models.PostMedia

    @staticmethod
    def resolve_url(root: models.PostMedia, info, *, size=None, format=None):
        if root.external_url:
            return root.external_url

        if not root.image:
            return

        if not size:
            return info.context.build_absolute_uri(root.image.url)

        format = format.lower() if format else None
        size = get_thumbnail_size(size)

        def _resolve_url(thumbnail):
            url = get_image_or_proxy_url(
                thumbnail, root.id, "PostMedia", size, format
            )
            return info.context.build_absolute_uri(url)

        return (
            ThumbnailByPostMediaIdSizeAndFormatLoader(info.context)
            .load((root.id, size, format))
            .then(_resolve_url)
        )

    @staticmethod
    def __resolve_references(roots: List["PostMedia"], _info):
        return resolve_federation_references(
            PostMedia, roots, models.PostMedia.objects
        )


class PostImage(graphene.ObjectType):
    id = graphene.ID(required=True, description="The ID of the image.")
    alt = graphene.String(description="The alt text of the image.")
    sort_order = graphene.Int(
        required=False,
        description=(
            "The new relative sorting position of the item (from -inf to +inf). "
            "1 moves the item one position forward, -1 moves the item one position "
            "backward, 0 leaves the item unchanged."
        ),
    )
    url = ThumbnailField(graphene.String, required=True)

    class Meta:
        description = "Represents a post image."

    @staticmethod
    def resolve_id(root: models.PostMedia, info):
        return graphene.Node.to_global_id("PostImage", root.id)

    @staticmethod
    def resolve_url(root: models.PostMedia, info, *, size=None, format=None):
        if not root.image:
            return

        if not size:
            return info.context.build_absolute_uri(root.image.url)

        format = format.lower() if format else None
        size = get_thumbnail_size(size)

        def _resolve_url(thumbnail):
            url = get_image_or_proxy_url(
                thumbnail, root.id, "PostMedia", size, format
            )
            return info.context.build_absolute_uri(url)

        return (
            ThumbnailByPostMediaIdSizeAndFormatLoader(info.context)
            .load((root.id, size, format))
            .then(_resolve_url)
        )


@federated_entity("id")
class Category(ModelObjectType):
    id = graphene.GlobalID(required=True)
    seo_title = graphene.String()
    seo_description = graphene.String()
    name = graphene.String(required=True)
    description = JSONString(description="Description of the category." + RICH_CONTENT)
    slug = graphene.String(required=True)
    parent = graphene.Field(lambda: Category)
    level = graphene.Int(required=True)
    description_json = JSONString(
        description="Description of the category." + RICH_CONTENT,
        deprecation_reason=(
            f"{DEPRECATED_IN_3X_FIELD} Use the `description` field instead."
        ),
    )
    ancestors = ConnectionField(
        lambda: CategoryCountableConnection,
        description="List of ancestors of the category.",
    )
    posts = ConnectionField(
        PostCountableConnection,
        # channel=graphene.String(
        #     description="Slug of a channel for which the data should be returned."
        # ),
        description=(
            "List of posts in the category. Requires the following permissions to "
            "include the unpublished items: "
            f"{', '.join([p.name for p in ALL_POSTS_PERMISSIONS])}."
        ),
    )
    children = ConnectionField(
        lambda: CategoryCountableConnection,
        description="List of children of the category.",
    )
    background_image = ThumbnailField()
    # translation = TranslationField(CategoryTranslation, type_name="category")

    class Meta:
        description = (
            "Represents a single category of posts. Categories allow to organize "
            "posts in a tree-hierarchies which can be used for navigation in the "
            "storefront."
        )
        interfaces = [relay.Node, ObjectWithMetadata]
        model = models.Category

    @staticmethod
    def resolve_ancestors(root: models.Category, info, **kwargs):
        return create_connection_slice(
            root.get_ancestors(), info, kwargs, CategoryCountableConnection
        )

    @staticmethod
    def resolve_description_json(root: models.Category, _info):
        description = root.description
        return description if description is not None else {}

    @staticmethod
    def resolve_background_image(root: models.Category, info, size=None, format=None):
        if not root.background_image:
            return

        alt = root.background_image_alt
        if not size:
            return Image(url=root.background_image.url, alt=alt)

        format = format.lower() if format else None
        size = get_thumbnail_size(size)

        def _resolve_background_image(thumbnail):
            url = get_image_or_proxy_url(thumbnail, root.id, "Category", size, format)
            return Image(url=url, alt=alt)

        return (
            ThumbnailByCategoryIdSizeAndFormatLoader(info.context)
            .load((root.id, size, format))
            .then(_resolve_background_image)
        )

    @staticmethod
    def resolve_children(root: models.Category, info, **kwargs):
        def slice_children_categories(children):
            return create_connection_slice(
                children, info, kwargs, CategoryCountableConnection
            )

        return (
            CategoryChildrenByCategoryIdLoader(info.context)
            .load(root.pk)
            .then(slice_children_categories)
        )

    @staticmethod
    def resolve_url(root: models.Category, _info):
        return ""

    @staticmethod
    @traced_resolver
    def resolve_posts(root: models.Category, info, *, channel=None, **kwargs):
        requestor = get_user_or_app_from_context(info.context)
        tree = root.get_descendants(include_self=True)
        qs.visible_to_user(requestor)
        qs = qs.filter(category__in=tree)
        return create_connection_slice(qs, info, kwargs, PostCountableConnection)

    @staticmethod
    def __resolve_references(roots: List["Category"], _info):
        return resolve_federation_references(Category, roots, models.Category.objects)


class CategoryCountableConnection(CountableConnection):
    class Meta:
        node = Category