import graphene
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Model
from graphql import GraphQLError

from ...core.permissions import SitePermissions
from ...core.tracing import traced_atomic_transaction
from ...menu import models as menu_models
from ...page import models as page_models
from ...post import models as post_models
from ...site.models import SiteSettings
from ..channel import ChannelContext
from ..core.descriptions import RICH_CONTENT
from ..core.enums import LanguageCodeEnum, TranslationErrorCode
from ..core.fields import JSONString
from ..core.mutations import BaseMutation, ModelMutation
from ..core.types import TranslationError
from ..core.utils import from_global_id_or_error
from ..menu.types import MenuItem
from . import types as translation_types

TRANSLATABLE_CONTENT_TO_MODEL = {
    # Page Translation mutation reverses model and TranslatableContent
    page_models.Page._meta.object_name: str(translation_types.PageTranslatableContent),
    post_models.Post._meta.object_name: str(translation_types.PostTranslatableContent),
    str(
        translation_types.MenuItemTranslatableContent
    ): menu_models.MenuItem._meta.object_name,
}


def validate_input_against_model(model: Model, input_data: dict):
    data_to_validate = {key: value for key, value in input_data.items() if value}
    instance = model(**data_to_validate)  # type: ignore
    all_fields = [field.name for field in model._meta.fields]
    exclude_fields = set(all_fields) - set(data_to_validate)
    instance.full_clean(exclude=exclude_fields, validate_unique=False)


class BaseTranslateMutation(ModelMutation):
    class Meta:
        abstract = True

    @classmethod
    def clean_node_id(cls, **data):
        if "id" in data and not data["id"]:
            raise ValidationError(
                {"id": ValidationError("This field is required", code="required")}
            )

        node_id = data["id"]
        try:
            node_type, node_pk = from_global_id_or_error(node_id)
        except GraphQLError:
            raise ValidationError(
                {
                    "id": ValidationError(
                        "Invalid ID has been provided.",
                        code=TranslationErrorCode.INVALID,
                    )
                }
            )

        # This mutation accepts either model IDs or translatable content IDs. Below we
        # check if provided ID refers to a translatable content which matches with the
        # expected model_type. If so, we transform the translatable content ID to model
        # ID.
        tc_model_type = TRANSLATABLE_CONTENT_TO_MODEL.get(node_type)

        if tc_model_type and tc_model_type == str(cls._meta.object_type):
            node_id = graphene.Node.to_global_id(tc_model_type, node_pk)

        return node_id, cls._meta.object_type

    @classmethod
    def validate_input(cls, input_data):
        validate_input_against_model(cls._meta.model, input_data)

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        node_id, model_type = cls.clean_node_id(**data)
        instance = cls.get_node_or_error(info, node_id, only_type=model_type)
        cls.validate_input(data["input"])

        translation, created = instance.translations.update_or_create(
            language_code=data["language_code"], defaults=data["input"]
        )

        def on_commit():
            if created:
                info.context.plugins.translation_created(translation)
            else:
                info.context.plugins.translation_updated(translation)

        transaction.on_commit(on_commit)
        return cls(**{cls._meta.return_field_name: instance})


class NameTranslationInput(graphene.InputObjectType):
    name = graphene.String()



class SeoTranslationInput(graphene.InputObjectType):
    seo_title = graphene.String()
    seo_description = graphene.String()


class TranslationInput(NameTranslationInput, SeoTranslationInput):
    description = JSONString(description="Translated description." + RICH_CONTENT)



class MenuItemTranslate(BaseTranslateMutation):
    class Arguments:
        id = graphene.ID(
            required=True, description="MenuItem ID or MenuItemTranslatableContent ID."
        )
        language_code = graphene.Argument(
            LanguageCodeEnum, required=True, description="Translation language code."
        )
        input = NameTranslationInput(required=True)

    class Meta:
        description = "Creates/updates translations for a menu item."
        model = menu_models.MenuItem
        object_type = MenuItem
        error_type_class = TranslationError
        error_type_field = "translation_errors"
        permissions = (SitePermissions.MANAGE_TRANSLATIONS,)

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        response = super().perform_mutation(_root, info, **data)
        instance = ChannelContext(node=response.menuItem, channel_slug=None)
        return cls(**{cls._meta.return_field_name: instance})


class PageTranslationInput(SeoTranslationInput):
    title = graphene.String()
    content = JSONString(description="Translated page content." + RICH_CONTENT)


class PageTranslate(BaseTranslateMutation):
    class Arguments:
        id = graphene.ID(
            required=True, description="Page ID or PageTranslatableContent ID."
        )
        language_code = graphene.Argument(
            LanguageCodeEnum, required=True, description="Translation language code."
        )
        input = PageTranslationInput(required=True)

    class Meta:
        description = "Creates/updates translations for a page."
        model = page_models.Page
        # Note: `PageTranslate` is only mutation that returns "TranslatableContent"
        object_type = translation_types.PageTranslatableContent
        error_type_class = TranslationError
        error_type_field = "translation_errors"
        permissions = (SitePermissions.MANAGE_TRANSLATIONS,)


class PostTranslationInput(SeoTranslationInput):
    title = graphene.String()
    content = JSONString(description="Translated page content." + RICH_CONTENT)


class PostTranslate(BaseTranslateMutation):
    class Arguments:
        id = graphene.ID(
            required=True, description="Post ID or PostTranslatableContent ID."
        )
        language_code = graphene.Argument(
            LanguageCodeEnum, required=True, description="Translation language code."
        )
        input = PostTranslationInput(required=True)

    class Meta:
        description = "Creates/updates translations for a post."
        model = post_models.Post
        # Note: `PostTranslate` is only mutation that returns "TranslatableContent"
        object_type = translation_types.PostTranslatableContent
        error_type_class = TranslationError
        error_type_field = "translation_errors"
        permissions = (SitePermissions.MANAGE_TRANSLATIONS,)

