from typing import List

import graphene
from django.conf import settings

from ...core.permissions import DiscountPermissions, ShippingPermissions
from ...core.tracing import traced_resolver
from ...menu import models as menu_models
from ...page import models as page_models
from ...post import models as post_models
from ...site import models as site_models
from ..channel import ChannelContext
from ..core.descriptions import DEPRECATED_IN_3X_FIELD, RICH_CONTENT
from ..core.enums import LanguageCodeEnum
from ..core.fields import JSONString, PermissionsField
from ..core.types import LanguageDisplay, ModelObjectType, NonNullList
from ..core.utils import str_to_enum
from .fields import TranslationField


class BaseTranslationType(ModelObjectType):
    language = graphene.Field(
        LanguageDisplay, description="Translation language.", required=True
    )

    class Meta:
        abstract = True

    @staticmethod
    @traced_resolver
    def resolve_language(root, _info):
        try:
            language = next(
                language[1]
                for language in settings.LANGUAGES
                if language[0] == root.language_code
            )
        except StopIteration:
            return None
        return LanguageDisplay(
            code=LanguageCodeEnum[str_to_enum(root.language_code)], language=language
        )


class PageTranslation(BaseTranslationType):
    id = graphene.GlobalID(required=True)
    seo_title = graphene.String()
    seo_description = graphene.String()
    title = graphene.String()
    content = JSONString(description="Translated content of the page." + RICH_CONTENT)
    content_json = JSONString(
        description="Translated description of the page." + RICH_CONTENT,
        deprecation_reason=f"{DEPRECATED_IN_3X_FIELD} Use the `content` field instead.",
    )

    class Meta:
        model = page_models.PageTranslation
        interfaces = [graphene.relay.Node]

    @staticmethod
    def resolve_content_json(root: page_models.PageTranslation, _info):
        content = root.content
        return content if content is not None else {}


class PostTranslation(BaseTranslationType):
    id = graphene.GlobalID(required=True)
    seo_title = graphene.String()
    seo_description = graphene.String()
    title = graphene.String()
    content = JSONString(description="Translated content of the post." + RICH_CONTENT)
    content_json = JSONString(
        description="Translated description of the post." + RICH_CONTENT,
        deprecation_reason=f"{DEPRECATED_IN_3X_FIELD} Use the `content` field instead.",
    )

    class Meta:
        model = post_models.PostTranslation
        interfaces = [graphene.relay.Node]

    @staticmethod
    def resolve_content_json(root: post_models.PostTranslation, _info):
        content = root.content
        return content if content is not None else {}


class PageTranslatableContent(ModelObjectType):
    id = graphene.GlobalID(required=True)
    seo_title = graphene.String()
    seo_description = graphene.String()
    title = graphene.String(required=True)
    content = JSONString(description="Content of the page." + RICH_CONTENT)
    content_json = JSONString(
        description="Content of the page." + RICH_CONTENT,
        deprecation_reason=f"{DEPRECATED_IN_3X_FIELD} Use the `content` field instead.",
    )
    translation = TranslationField(PageTranslation, type_name="page")
    page = graphene.Field(
        "cms.graphql.page.types.Page",
        description=(
            "A static page that can be manually added by a shop operator "
            "through the dashboard."
        ),
        deprecation_reason=(
            f"{DEPRECATED_IN_3X_FIELD} Get model fields from the root level queries."
        ),
    )

    class Meta:
        model = page_models.Page
        interfaces = [graphene.relay.Node]

    @staticmethod
    def resolve_page(root: page_models.Page, info):
        return (
            page_models.Page.objects.visible_to_user(info.context.user)
            .filter(pk=root.id)
            .first()
        )

    @staticmethod
    def resolve_content_json(root: page_models.Page, _info):
        content = root.content
        return content if content is not None else {}


class PostTranslatableContent(ModelObjectType):
    id = graphene.GlobalID(required=True)
    seo_title = graphene.String()
    seo_description = graphene.String()
    title = graphene.String(required=True)
    content = JSONString(description="Content of the post." + RICH_CONTENT)
    content_json = JSONString(
        description="Content of the page." + RICH_CONTENT,
        deprecation_reason=f"{DEPRECATED_IN_3X_FIELD} Use the `content` field instead.",
    )
    translation = TranslationField(PostTranslation, type_name="page")
    post = graphene.Field(
        "cms.graphql.post.types.Post",
        description=(
            "A static page that can be manually added by a shop operator "
            "through the dashboard."
        ),
        deprecation_reason=(
            f"{DEPRECATED_IN_3X_FIELD} Get model fields from the root level queries."
        ),
    )

    class Meta:
        model = post_models.Post
        interfaces = [graphene.relay.Node]

    @staticmethod
    def resolve_post(root: post_models.Post, info):
        return (
            post_models.Post.objects.visible_to_user(info.context.user)
            .filter(pk=root.id)
            .first()
        )

    @staticmethod
    def resolve_content_json(root: post_models.Post, _info):
        content = root.content
        return content if content is not None else {}



class MenuItemTranslation(BaseTranslationType):
    id = graphene.GlobalID(required=True)
    name = graphene.String(required=True)

    class Meta:
        model = menu_models.MenuItemTranslation
        interfaces = [graphene.relay.Node]


class MenuItemTranslatableContent(ModelObjectType):
    id = graphene.GlobalID(required=True)
    name = graphene.String(required=True)
    translation = TranslationField(MenuItemTranslation, type_name="menu item")
    menu_item = graphene.Field(
        "cms.graphql.menu.types.MenuItem",
        description=(
            "Represents a single item of the related menu. Can store categories, "
            "collection or pages."
        ),
        deprecation_reason=(
            f"{DEPRECATED_IN_3X_FIELD} Get model fields from the root level queries."
        ),
    )

    class Meta:
        model = menu_models.MenuItem
        interfaces = [graphene.relay.Node]

    @staticmethod
    def resolve_menu_item(root: menu_models.MenuItem, _info):
        return ChannelContext(node=root, channel_slug=None)
