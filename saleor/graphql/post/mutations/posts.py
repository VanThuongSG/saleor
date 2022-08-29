from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List

import graphene
import pytz
from django.core.exceptions import ValidationError
from django.db import transaction

from ....attribute import AttributeInputType, AttributeType
from ....attribute import models as attribute_models
from ....core.permissions import PostPermissions, PostTypePermissions
from ....core.tracing import traced_atomic_transaction
from ....post import models
from ....post.error_codes import PostErrorCode
from ...attribute.types import AttributeValueInput
from ...attribute.utils import AttributeAssignmentMixin
from ...core.descriptions import ADDED_IN_33, DEPRECATED_IN_3X_INPUT, RICH_CONTENT
from ...core.fields import JSONString
from ...core.mutations import ModelDeleteMutation, ModelMutation
from ...core.types import NonNullList, PostError, SeoInput
from ...core.utils import clean_seo_fields, validate_slug_and_generate_if_needed
from ...utils.validators import check_for_duplicates
from ..types import Post, PostType

if TYPE_CHECKING:
    from ....attribute.models import Attribute


class PostInput(graphene.InputObjectType):
    slug = graphene.String(description="Post internal name.")
    title = graphene.String(description="Post title.")
    content = JSONString(description="Post content." + RICH_CONTENT)
    attributes = NonNullList(AttributeValueInput, description="List of attributes.")
    is_published = graphene.Boolean(
        description="Determines if post is visible in the storefront."
    )
    publication_date = graphene.String(
        description=(
            f"Publication date. ISO 8601 standard. {DEPRECATED_IN_3X_INPUT} "
            "Use `publishedAt` field instead."
        )
    )
    published_at = graphene.DateTime(
        description="Publication date time. ISO 8601 standard." + ADDED_IN_33
    )
    seo = SeoInput(description="Search engine optimization fields.")


class PostCreateInput(PostInput):
    post_type = graphene.ID(
        description="ID of the post type that post belongs to.", required=True
    )


class PostCreate(ModelMutation):
    class Arguments:
        input = PostCreateInput(
            required=True, description="Fields required to create a post."
        )

    class Meta:
        description = "Creates a new post."
        model = models.Post
        object_type = Post
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def clean_attributes(cls, attributes: dict, post_type: models.PostType):
        attributes_qs = post_type.post_attributes
        attributes = AttributeAssignmentMixin.clean_input(
            attributes, attributes_qs, is_post_attributes=True
        )
        return attributes

    @classmethod
    def clean_input(cls, info, instance, data):
        cleaned_input = super().clean_input(info, instance, data)
        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "title", cleaned_input
            )
        except ValidationError as error:
            error.code = PostErrorCode.REQUIRED
            raise ValidationError({"slug": error})

        if "publication_date" in cleaned_input and "published_at" in cleaned_input:
            raise ValidationError(
                {
                    "publication_date": ValidationError(
                        "Only one of argument: publicationDate or publishedAt "
                        "must be specified.",
                        code=PostErrorCode.INVALID.value,
                    )
                }
            )

        is_published = cleaned_input.get("is_published")
        publication_date = cleaned_input.get("published_at") or cleaned_input.get(
            "publication_date"
        )
        if is_published and not publication_date:
            cleaned_input["published_at"] = datetime.now(pytz.UTC)
        elif "publication_date" in cleaned_input or "published_at" in cleaned_input:
            cleaned_input["published_at"] = publication_date

        attributes = cleaned_input.get("attributes")
        post_type = (
            instance.post_type if instance.pk else cleaned_input.get("post_type")
        )
        if attributes and post_type:
            try:
                cleaned_input["attributes"] = cls.clean_attributes(
                    attributes, post_type
                )
            except ValidationError as exc:
                raise ValidationError({"attributes": exc})

        clean_seo_fields(cleaned_input)

        return cleaned_input

    @classmethod
    @traced_atomic_transaction()
    def _save_m2m(cls, info, instance, cleaned_data):
        super()._save_m2m(info, instance, cleaned_data)

        attributes = cleaned_data.get("attributes")
        if attributes:
            AttributeAssignmentMixin.save(instance, attributes)

    @classmethod
    def save(cls, info, instance, cleaned_input):
        super().save(info, instance, cleaned_input)
        info.context.plugins.post_created(instance)


class PostUpdate(PostCreate):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a post to update.")
        input = PostInput(
            required=True, description="Fields required to update a post."
        )

    class Meta:
        description = "Updates an existing post."
        model = models.Post
        object_type = Post
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def clean_attributes(cls, attributes: dict, post_type: models.PostType):
        attributes_qs = post_type.post_attributes
        attributes = AttributeAssignmentMixin.clean_input(
            attributes, attributes_qs, creation=False, is_post_attributes=True
        )
        return attributes

    @classmethod
    def save(cls, info, instance, cleaned_input):
        super(PostCreate, cls).save(info, instance, cleaned_input)
        info.context.plugins.post_updated(instance)


class PostDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a post to delete.")

    class Meta:
        description = "Deletes a post."
        model = models.Post
        object_type = Post
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    @traced_atomic_transaction()
    def perform_mutation(cls, _root, info, **data):
        post = cls.get_instance(info, **data)
        cls.delete_assigned_attribute_values(post)
        response = super().perform_mutation(_root, info, **data)
        transaction.on_commit(lambda: info.context.plugins.post_deleted(post))
        return response

    @staticmethod
    def delete_assigned_attribute_values(instance):
        attribute_models.AttributeValue.objects.filter(
            postassignments__post_id=instance.id,
            attribute__input_type__in=AttributeInputType.TYPES_WITH_UNIQUE_VALUES,
        ).delete()


class PostTypeCreateInput(graphene.InputObjectType):
    name = graphene.String(description="Name of the post type.")
    slug = graphene.String(description="Post type slug.")
    add_attributes = NonNullList(
        graphene.ID,
        description="List of attribute IDs to be assigned to the post type.",
    )


class PostTypeUpdateInput(PostTypeCreateInput):
    remove_attributes = NonNullList(
        graphene.ID,
        description="List of attribute IDs to be assigned to the post type.",
    )


class PostTypeMixin:
    @classmethod
    def validate_attributes(
        cls,
        errors: Dict[str, List[ValidationError]],
        attributes: List["Attribute"],
        field: str,
    ):
        """All attributes must be post type attribute.

        Raise an error if any of the attributes are not post attribute.
        """
        if attributes:
            not_valid_attributes = [
                graphene.Node.to_global_id("Attribute", attr.pk)
                for attr in attributes
                if attr.type != AttributeType.POST_TYPE
            ]
            if not_valid_attributes:
                error = ValidationError(
                    "Only post type attributes allowed.",
                    code=PostErrorCode.INVALID.value,
                    params={"attributes": not_valid_attributes},
                )
                errors[field].append(error)


class PostTypeCreate(PostTypeMixin, ModelMutation):
    class Arguments:
        input = PostTypeCreateInput(
            description="Fields required to create post type.", required=True
        )

    class Meta:
        description = "Create a new post type."
        model = models.PostType
        object_type = PostType
        permissions = (PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def clean_input(cls, info, instance, data):
        cleaned_input = super().clean_input(info, instance, data)
        errors = defaultdict(list)
        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "name", cleaned_input
            )
        except ValidationError as error:
            error.code = PostErrorCode.REQUIRED.value
            errors["slug"].append(error)

        cls.validate_attributes(
            errors, cleaned_input.get("add_attributes"), "add_attributes"
        )

        if errors:
            raise ValidationError(errors)

        return cleaned_input

    @classmethod
    def _save_m2m(cls, info, instance, cleaned_data):
        super()._save_m2m(info, instance, cleaned_data)
        attributes = cleaned_data.get("add_attributes")
        if attributes is not None:
            instance.post_attributes.add(*attributes)

    @classmethod
    def post_save_action(cls, info, instance, cleaned_input):
        info.context.plugins.post_type_created(instance)


class PostTypeUpdate(PostTypeMixin, ModelMutation):
    class Arguments:
        id = graphene.ID(description="ID of the post type to update.")
        input = PostTypeUpdateInput(
            description="Fields required to update post type.", required=True
        )

    class Meta:
        description = "Update post type."
        model = models.PostType
        object_type = PostType
        permissions = (PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def clean_input(cls, info, instance, data):
        errors = defaultdict(list)
        error = check_for_duplicates(
            data, "add_attributes", "remove_attributes", "attributes"
        )
        if error:
            error.code = PostErrorCode.DUPLICATED_INPUT_ITEM.value
            errors["attributes"].append(error)

        cleaned_input = super().clean_input(info, instance, data)
        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "name", cleaned_input
            )
        except ValidationError as error:
            error.code = PostErrorCode.REQUIRED
            errors["slug"].append(error)

        add_attributes = cleaned_input.get("add_attributes")
        cls.validate_attributes(errors, add_attributes, "add_attributes")

        remove_attributes = cleaned_input.get("remove_attributes")
        cls.validate_attributes(errors, remove_attributes, "remove_attributes")

        if errors:
            raise ValidationError(errors)

        return cleaned_input

    @classmethod
    def _save_m2m(cls, info, instance, cleaned_data):
        super()._save_m2m(info, instance, cleaned_data)
        remove_attributes = cleaned_data.get("remove_attributes")
        add_attributes = cleaned_data.get("add_attributes")
        if remove_attributes is not None:
            instance.post_attributes.remove(*remove_attributes)
        if add_attributes is not None:
            instance.post_attributes.add(*add_attributes)

    @classmethod
    def post_save_action(cls, info, instance, cleaned_input):
        info.context.plugins.post_type_updated(instance)


class PostTypeDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of the post type to delete.")

    class Meta:
        description = "Delete a post type."
        model = models.PostType
        object_type = PostType
        permissions = (PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    @traced_atomic_transaction()
    def perform_mutation(cls, _root, info, **data):
        node_id = data.get("id")
        post_type_pk = cls.get_global_id_or_error(
            node_id, only_type=PostType, field="pk"
        )
        cls.delete_assigned_attribute_values(post_type_pk)
        return super().perform_mutation(_root, info, **data)

    @staticmethod
    def delete_assigned_attribute_values(instance_pk):
        attribute_models.AttributeValue.objects.filter(
            attribute__input_type__in=AttributeInputType.TYPES_WITH_UNIQUE_VALUES,
            postassignments__assignment__post_type_id=instance_pk,
        ).delete()

    @classmethod
    def post_save_action(cls, info, instance, cleaned_input):
        transaction.on_commit(lambda: info.context.plugins.post_type_deleted(instance))
