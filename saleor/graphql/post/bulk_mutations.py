import graphene
from django.core.exceptions import ValidationError
from django.db import transaction

from ...attribute import AttributeInputType
from ...attribute import models as attribute_models
from ...core.permissions import PostPermissions, PostTypePermissions
from ...core.tracing import traced_atomic_transaction
from ...post import models
from ..core.mutations import BaseBulkMutation, ModelBulkDeleteMutation
from ..core.types import NonNullList, PostError
from .types import Post, PostType, PostMedia


class PostBulkDelete(ModelBulkDeleteMutation):
    class Arguments:
        ids = NonNullList(
            graphene.ID, required=True, description="List of post IDs to delete."
        )

    class Meta:
        description = "Deletes posts."
        model = models.Post
        object_type = Post
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    @traced_atomic_transaction()
    def perform_mutation(cls, _root, info, ids, **data):
        try:
            pks = cls.get_global_ids_or_error(ids, only_type=Post, field="pk")
        except ValidationError as error:
            return 0, error
        cls.delete_assigned_attribute_values(pks)
        return super().perform_mutation(_root, info, ids, **data)

    @staticmethod
    def delete_assigned_attribute_values(instance_pks):
        attribute_models.AttributeValue.objects.filter(
            postassignments__post_id__in=instance_pks,
            attribute__input_type__in=AttributeInputType.TYPES_WITH_UNIQUE_VALUES,
        ).delete()


class PostBulkPublish(BaseBulkMutation):
    class Arguments:
        ids = NonNullList(
            graphene.ID, required=True, description="List of post IDs to (un)publish."
        )
        is_published = graphene.Boolean(
            required=True, description="Determine if posts will be published or not."
        )

    class Meta:
        description = "Publish posts."
        model = models.Post
        object_type = Post
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def bulk_action(cls, info, queryset, is_published):
        queryset.update(is_published=is_published)


class PostTypeBulkDelete(ModelBulkDeleteMutation):
    class Arguments:
        ids = NonNullList(
            graphene.ID,
            description="List of post type IDs to delete",
            required=True,
        )

    class Meta:
        description = "Delete post types."
        model = models.PostType
        object_type = PostType
        permissions = (PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    @traced_atomic_transaction()
    def perform_mutation(cls, _root, info, ids, **data):
        try:
            pks = cls.get_global_ids_or_error(ids, only_type=PostType, field="pk")
        except ValidationError as error:
            return 0, error
        cls.delete_assigned_attribute_values(pks)
        return super().perform_mutation(_root, info, ids, **data)

    @classmethod
    def bulk_action(cls, info, queryset):
        post_types = list(queryset)
        queryset.delete()
        for pt in post_types:
            transaction.on_commit(lambda: info.context.plugins.post_type_deleted(pt))

    @staticmethod
    def delete_assigned_attribute_values(instance_pks):
        attribute_models.AttributeValue.objects.filter(
            postassignments__assignment__post_type_id__in=instance_pks,
            attribute__input_type__in=AttributeInputType.TYPES_WITH_UNIQUE_VALUES,
        ).delete()


class PostMediaBulkDelete(ModelBulkDeleteMutation):
    class Arguments:
        ids = NonNullList(
            graphene.ID,
            required=True,
            description="List of product media IDs to delete.",
        )

    class Meta:
        description = "Deletes product media."
        model = models.PostMedia
        object_type = PostMedia
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"
