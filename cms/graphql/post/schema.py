import graphene

from ..core.connection import create_connection_slice, filter_connection_queryset
from ..core.fields import FilterConnectionField
from ..core.utils import from_global_id_or_error
from ..translations.mutations import PostTranslate
from .bulk_mutations import (
    PostBulkDelete,
    PostBulkPublish,
    PostTypeBulkDelete,
    PostMediaBulkDelete
)
from .filters import PostFilterInput, PostTypeFilterInput

from .mutations.posts import (
    PostCreate,
    PostDelete,
    PostTypeCreate,
    PostTypeDelete,
    PostTypeUpdate,
    PostUpdate,
    PostMediaCreate,
    PostMediaDelete,
    PostMediaReorder,
    PostMediaUpdate,
)
from .resolvers import (
    resolve_post,
    resolve_post_type,
    resolve_post_types,
    resolve_posts,
)
from .sorters import PostSortingInput, PostTypeSortingInput
from .types import Post, PostCountableConnection, PostType, PostTypeCountableConnection


class PostQueries(graphene.ObjectType):
    post = graphene.Field(
        Post,
        id=graphene.Argument(graphene.ID, description="ID of the post."),
        slug=graphene.String(description="The slug of the post."),
        description="Look up a post by ID or slug.",
    )
    posts = FilterConnectionField(
        PostCountableConnection,
        sort_by=PostSortingInput(description="Sort posts."),
        filter=PostFilterInput(description="Filtering options for posts."),
        description="List of the shop's posts.",
    )
    post_type = graphene.Field(
        PostType,
        id=graphene.Argument(
            graphene.ID, description="ID of the post type.", required=True
        ),
        description="Look up a post type by ID.",
    )
    post_types = FilterConnectionField(
        PostTypeCountableConnection,
        sort_by=PostTypeSortingInput(description="Sort post types."),
        filter=PostTypeFilterInput(description="Filtering options for post types."),
        description="List of the post types.",
    )

    @staticmethod
    def resolve_post(_root, info, *, id=None, slug=None):
        return resolve_post(info, id, slug)

    @staticmethod
    def resolve_posts(_root, info, **kwargs):
        qs = resolve_posts(info)
        qs = filter_connection_queryset(qs, kwargs)
        return create_connection_slice(qs, info, kwargs, PostCountableConnection)

    @staticmethod
    def resolve_post_type(_root, info, *, id):
        _, id = from_global_id_or_error(id, PostType)
        return resolve_post_type(id)

    @staticmethod
    def resolve_post_types(_root, info, **kwargs):
        qs = resolve_post_types(info)
        qs = filter_connection_queryset(qs, kwargs)
        return create_connection_slice(qs, info, kwargs, PostTypeCountableConnection)


class PostMutations(graphene.ObjectType):
    # post mutations
    post_create = PostCreate.Field()
    post_delete = PostDelete.Field()
    post_bulk_delete = PostBulkDelete.Field()
    post_bulk_publish = PostBulkPublish.Field()
    post_update = PostUpdate.Field()
    post_translate = PostTranslate.Field()

    post_media_create = PostMediaCreate.Field()
    post_media_delete = PostMediaDelete.Field()
    post_media_bulk_delete = PostMediaBulkDelete.Field()
    post_media_reorder = PostMediaReorder.Field()
    post_media_update = PostMediaUpdate.Field()

    # post type mutations
    post_type_create = PostTypeCreate.Field()
    post_type_update = PostTypeUpdate.Field()
    post_type_delete = PostTypeDelete.Field()
    post_type_bulk_delete = PostTypeBulkDelete.Field()
