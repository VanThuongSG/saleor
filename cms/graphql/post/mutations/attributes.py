from collections import defaultdict
from typing import Dict, List

import graphene
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from ....attribute import AttributeType, models
from ....core.permissions import PostPermissions, PostTypePermissions
from ....core.tracing import traced_atomic_transaction
from ....post import models as post_models
from ....post.error_codes import PostErrorCode
from ...attribute.mutations import (
    BaseReorderAttributesMutation,
    BaseReorderAttributeValuesMutation,
)
from ...attribute.types import Attribute
from ...core.inputs import ReorderInput
from ...core.mutations import BaseMutation
from ...core.types import NonNullList, PostError
from ...core.utils.reordering import perform_reordering
from ...post.types import Post, PostType
from ...utils import resolve_global_ids_to_primary_keys


class PostAttributeAssign(BaseMutation):
    post_type = graphene.Field(PostType, description="The updated post type.")

    class Arguments:
        post_type_id = graphene.ID(
            required=True,
            description="ID of the post type to assign the attributes into.",
        )
        attribute_ids = NonNullList(
            graphene.ID,
            required=True,
            description="The IDs of the attributes to assign.",
        )

    class Meta:
        description = "Assign attributes to a given post type."
        error_type_class = PostError
        error_type_field = "post_errors"
        permissions = (PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES,)

    @classmethod
    def clean_attributes(
        cls,
        errors: Dict["str", List[ValidationError]],
        post_type: "post_models.PostType",
        attr_pks: List[int],
    ):
        """Ensure the attributes are post attributes and are not already assigned."""

        # check if any attribute is not a post type
        invalid_attributes = models.Attribute.objects.filter(pk__in=attr_pks).exclude(
            type=AttributeType.POST_TYPE
        )

        if invalid_attributes:
            invalid_attributes_ids = [
                graphene.Node.to_global_id("Attribute", attr.pk)
                for attr in invalid_attributes
            ]
            error = ValidationError(
                "Only post attributes can be assigned.",
                code=PostErrorCode.INVALID.value,
                params={"attributes": invalid_attributes_ids},
            )
            errors["attribute_ids"].append(error)

        # check if any attribute is already assigned to this post type
        assigned_attrs = models.Attribute.objects.get_assigned_post_type_attributes(
            post_type.pk
        ).filter(pk__in=attr_pks)

        if assigned_attrs:
            assigned_attributes_ids = [
                graphene.Node.to_global_id("Attribute", attr.pk)
                for attr in assigned_attrs
            ]
            error = ValidationError(
                "Some of the attributes have been already assigned to this post type.",
                code=PostErrorCode.ATTRIBUTE_ALREADY_ASSIGNED.value,
                params={"attributes": assigned_attributes_ids},
            )
            errors["attribute_ids"].append(error)

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        errors = defaultdict(list)
        post_type_id: str = data["post_type_id"]
        attribute_ids = data["attribute_ids"]

        # retrieve the requested post type
        post_type = cls.get_node_or_error(
            info, post_type_id, only_type=PostType, field="post_type_id"
        )

        # resolve all passed attributes IDs to attributes pks
        attr_pks = cls.get_global_ids_or_error(
            attribute_ids, Attribute, field="attribute_ids"
        )

        # ensure the attributes are assignable
        cls.clean_attributes(errors, post_type, attr_pks)

        if errors:
            raise ValidationError(errors)

        post_type.post_attributes.add(*attr_pks)

        return cls(post_type=post_type)


class PostAttributeUnassign(BaseMutation):
    post_type = graphene.Field(PostType, description="The updated post type.")

    class Arguments:
        post_type_id = graphene.ID(
            required=True,
            description=(
                "ID of the post type from which the attributes should be unassign."
            ),
        )
        attribute_ids = NonNullList(
            graphene.ID,
            required=True,
            description="The IDs of the attributes to unassign.",
        )

    class Meta:
        description = "Unassign attributes from a given post type."
        permissions = (PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        post_type_id = data["post_type_id"]
        attribute_ids = data["attribute_ids"]

        # retrieve the requested post type
        post_type = cls.get_node_or_error(info, post_type_id, only_type=PostType)

        # resolve all passed attributes IDs to attributes pks
        _, attr_pks = resolve_global_ids_to_primary_keys(attribute_ids, Attribute)

        post_type.post_attributes.remove(*attr_pks)

        return cls(post_type=post_type)


class PostTypeReorderAttributes(BaseReorderAttributesMutation):
    post_type = graphene.Field(
        PostType, description="Post type from which attributes are reordered."
    )

    class Arguments:
        post_type_id = graphene.Argument(
            graphene.ID, required=True, description="ID of a post type."
        )
        moves = NonNullList(
            ReorderInput,
            required=True,
            description="The list of attribute reordering operations.",
        )

    class Meta:
        description = "Reorder the attributes of a post type."
        permissions = (PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        post_type_id = data["post_type_id"]
        pk = cls.get_global_id_or_error(post_type_id, only_type=PostType, field="pk")

        try:
            post_type = post_models.PostType.objects.prefetch_related(
                "attributepost"
            ).get(pk=pk)
        except ObjectDoesNotExist:
            raise ValidationError(
                {
                    "post_type_id": ValidationError(
                        f"Couldn't resolve to a post type: {post_type_id}",
                        code=PostErrorCode.NOT_FOUND.value,
                    )
                }
            )

        post_attributes = post_type.attributepost.all()
        moves = data["moves"]

        try:
            operations = cls.prepare_operations(moves, post_attributes)
        except ValidationError as error:
            error.code = PostErrorCode.NOT_FOUND.value
            raise ValidationError({"moves": error})

        with traced_atomic_transaction():
            perform_reordering(post_attributes, operations)

        return PostTypeReorderAttributes(post_type=post_type)


class PostReorderAttributeValues(BaseReorderAttributeValuesMutation):
    post = graphene.Field(
        Post, description="Post from which attribute values are reordered."
    )

    class Meta:
        description = "Reorder post attribute values."
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    class Arguments:
        post_id = graphene.Argument(
            graphene.ID, required=True, description="ID of a post."
        )
        attribute_id = graphene.Argument(
            graphene.ID, required=True, description="ID of an attribute."
        )
        moves = NonNullList(
            ReorderInput,
            required=True,
            description="The list of reordering operations for given attribute values.",
        )

    @classmethod
    def perform_mutation(cls, _root, _info, **data):
        post_id = data["post_id"]
        post = cls.perform(post_id, "post", data, "postvalueassignment", PostErrorCode)
        return PostReorderAttributeValues(post=post)

    @classmethod
    def get_instance(cls, instance_id: str):
        pk = cls.get_global_id_or_error(instance_id, only_type=Post, field="post_id")

        try:
            post = post_models.Post.objects.prefetch_related("attributes").get(pk=pk)
        except ObjectDoesNotExist:
            raise ValidationError(
                {
                    "post_id": ValidationError(
                        (f"Couldn't resolve to a post: {instance_id}"),
                        code=PostErrorCode.NOT_FOUND.value,
                    )
                }
            )
        return post
