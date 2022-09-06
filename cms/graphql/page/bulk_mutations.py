import graphene
from django.core.exceptions import ValidationError
from django.db import transaction

from ...core.permissions import PagePermissions, PageTypePermissions
from ...core.tracing import traced_atomic_transaction
from ...page import models
from ..core.mutations import BaseBulkMutation, ModelBulkDeleteMutation
from ..core.types import NonNullList, PageError
from .types import Page, PageType


class PageBulkDelete(ModelBulkDeleteMutation):
    class Arguments:
        ids = NonNullList(
            graphene.ID, required=True, description="List of page IDs to delete."
        )

    class Meta:
        description = "Deletes pages."
        model = models.Page
        object_type = Page
        permissions = (PagePermissions.MANAGE_PAGES,)
        error_type_class = PageError
        error_type_field = "page_errors"

    @classmethod
    @traced_atomic_transaction()
    def perform_mutation(cls, _root, info, ids, **data):
        try:
            pks = cls.get_global_ids_or_error(ids, only_type=Page, field="pk")
        except ValidationError as error:
            return 0, error
        cls.delete_assigned_attribute_values(pks)
        return super().perform_mutation(_root, info, ids, **data)


class PageBulkPublish(BaseBulkMutation):
    class Arguments:
        ids = NonNullList(
            graphene.ID, required=True, description="List of page IDs to (un)publish."
        )
        is_published = graphene.Boolean(
            required=True, description="Determine if pages will be published or not."
        )

    class Meta:
        description = "Publish pages."
        model = models.Page
        object_type = Page
        permissions = (PagePermissions.MANAGE_PAGES,)
        error_type_class = PageError
        error_type_field = "page_errors"

    @classmethod
    def bulk_action(cls, info, queryset, is_published):
        queryset.update(is_published=is_published)


class PageTypeBulkDelete(ModelBulkDeleteMutation):
    class Arguments:
        ids = NonNullList(
            graphene.ID,
            description="List of page type IDs to delete",
            required=True,
        )

    class Meta:
        description = "Delete page types."
        model = models.PageType
        object_type = PageType
        permissions = (PageTypePermissions.MANAGE_PAGE_TYPES_AND_ATTRIBUTES,)
        error_type_class = PageError
        error_type_field = "page_errors"

    @classmethod
    @traced_atomic_transaction()
    def perform_mutation(cls, _root, info, ids, **data):
        try:
            pks = cls.get_global_ids_or_error(ids, only_type=PageType, field="pk")
        except ValidationError as error:
            return 0, error
        cls.delete_assigned_attribute_values(pks)
        return super().perform_mutation(_root, info, ids, **data)

    @classmethod
    def bulk_action(cls, info, queryset):
        page_types = list(queryset)
        queryset.delete()
        for pt in page_types:
            transaction.on_commit(lambda: info.context.plugins.page_type_deleted(pt))