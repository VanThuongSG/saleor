from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List

import graphene
import pytz
from django.core.exceptions import ValidationError
from django.db import transaction


from ....core.permissions import PagePermissions, PageTypePermissions
from ....core.tracing import traced_atomic_transaction
from ....page import models
from ....page.error_codes import PageErrorCode
from ...core.descriptions import ADDED_IN_33, DEPRECATED_IN_3X_INPUT, RICH_CONTENT
from ...core.fields import JSONString
from ...core.mutations import ModelDeleteMutation, ModelMutation
from ...core.types import NonNullList, PageError, SeoInput
from ...core.utils import clean_seo_fields, validate_slug_and_generate_if_needed
from ...utils.validators import check_for_duplicates
from ..types import Page, PageType


class PageInput(graphene.InputObjectType):
    slug = graphene.String(description="Page internal name.")
    title = graphene.String(description="Page title.")
    content = JSONString(description="Page content." + RICH_CONTENT)
    is_published = graphene.Boolean(
        description="Determines if page is visible in the storefront."
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


class PageCreateInput(PageInput):
    page_type = graphene.ID(
        description="ID of the page type that page belongs to.", required=True
    )


class PageCreate(ModelMutation):
    class Arguments:
        input = PageCreateInput(
            required=True, description="Fields required to create a page."
        )

    class Meta:
        description = "Creates a new page."
        model = models.Page
        object_type = Page
        permissions = (PagePermissions.MANAGE_PAGES,)
        error_type_class = PageError
        error_type_field = "page_errors"


    @classmethod
    def clean_input(cls, info, instance, data):
        cleaned_input = super().clean_input(info, instance, data)
        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "title", cleaned_input
            )
        except ValidationError as error:
            error.code = PageErrorCode.REQUIRED
            raise ValidationError({"slug": error})

        if "publication_date" in cleaned_input and "published_at" in cleaned_input:
            raise ValidationError(
                {
                    "publication_date": ValidationError(
                        "Only one of argument: publicationDate or publishedAt "
                        "must be specified.",
                        code=PageErrorCode.INVALID.value,
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

        clean_seo_fields(cleaned_input)

        return cleaned_input

    @classmethod
    @traced_atomic_transaction()
    def _save_m2m(cls, info, instance, cleaned_data):
        super()._save_m2m(info, instance, cleaned_data)
    
    @classmethod
    def save(cls, info, instance, cleaned_input):
        super().save(info, instance, cleaned_input)
        info.context.plugins.page_created(instance)


class PageUpdate(PageCreate):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a page to update.")
        input = PageInput(
            required=True, description="Fields required to update a page."
        )

    class Meta:
        description = "Updates an existing page."
        model = models.Page
        object_type = Page
        permissions = (PagePermissions.MANAGE_PAGES,)
        error_type_class = PageError
        error_type_field = "page_errors"


    @classmethod
    def save(cls, info, instance, cleaned_input):
        super(PageCreate, cls).save(info, instance, cleaned_input)
        info.context.plugins.page_updated(instance)


class PageDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a page to delete.")

    class Meta:
        description = "Deletes a page."
        model = models.Page
        object_type = Page
        permissions = (PagePermissions.MANAGE_PAGES,)
        error_type_class = PageError
        error_type_field = "page_errors"

    @classmethod
    @traced_atomic_transaction()
    def perform_mutation(cls, _root, info, **data):
        page = cls.get_instance(info, **data)
        cls.delete_assigned_attribute_values(page)
        response = super().perform_mutation(_root, info, **data)
        transaction.on_commit(lambda: info.context.plugins.page_deleted(page))
        return response


class PageTypeCreateInput(graphene.InputObjectType):
    name = graphene.String(description="Name of the page type.")
    slug = graphene.String(description="Page type slug.")


class PageTypeCreate(ModelMutation):
    class Arguments:
        input = PageTypeCreateInput(
            description="Fields required to create page type.", required=True
        )

    class Meta:
        description = "Create a new page type."
        model = models.PageType
        object_type = PageType
        permissions = (PageTypePermissions.MANAGE_PAGE_TYPES_AND_ATTRIBUTES,)
        error_type_class = PageError
        error_type_field = "page_errors"

    @classmethod
    def clean_input(cls, info, instance, data):
        cleaned_input = super().clean_input(info, instance, data)
        errors = defaultdict(list)
        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "name", cleaned_input
            )
        except ValidationError as error:
            error.code = PageErrorCode.REQUIRED.value
            errors["slug"].append(error)

        if errors:
            raise ValidationError(errors)

        return cleaned_input

    @classmethod
    def _save_m2m(cls, info, instance, cleaned_data):
        super()._save_m2m(info, instance, cleaned_data)

    @classmethod
    def post_save_action(cls, info, instance, cleaned_input):
        info.context.plugins.page_type_created(instance)


class PageTypeUpdate(ModelMutation):
    class Arguments:
        id = graphene.ID(description="ID of the page type to update.")
        input = PageTypeCreateInput(
            description="Fields required to update page type.", required=True
        )

    class Meta:
        description = "Update page type."
        model = models.PageType
        object_type = PageType
        permissions = (PageTypePermissions.MANAGE_PAGE_TYPES_AND_ATTRIBUTES,)
        error_type_class = PageError
        error_type_field = "page_errors"

    @classmethod
    def clean_input(cls, info, instance, data):
        errors = defaultdict(list)
        error = check_for_duplicates(data)
        if error:
            error.code = PageErrorCode.DUPLICATED_INPUT_ITEM.value
            errors["attributes"].append(error)

        cleaned_input = super().clean_input(info, instance, data)
        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "name", cleaned_input
            )
        except ValidationError as error:
            error.code = PageErrorCode.REQUIRED
            errors["slug"].append(error)

        if errors:
            raise ValidationError(errors)

        return cleaned_input

    @classmethod
    def _save_m2m(cls, info, instance, cleaned_data):
        super()._save_m2m(info, instance, cleaned_data)

    @classmethod
    def post_save_action(cls, info, instance, cleaned_input):
        info.context.plugins.page_type_updated(instance)


class PageTypeDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of the page type to delete.")

    class Meta:
        description = "Delete a page type."
        model = models.PageType
        object_type = PageType
        permissions = (PageTypePermissions.MANAGE_PAGE_TYPES_AND_ATTRIBUTES,)
        error_type_class = PageError
        error_type_field = "page_errors"

    @classmethod
    @traced_atomic_transaction()
    def perform_mutation(cls, _root, info, **data):
        return super().perform_mutation(_root, info, **data)


    @classmethod
    def post_save_action(cls, info, instance, cleaned_input):
        transaction.on_commit(lambda: info.context.plugins.page_type_deleted(instance))
