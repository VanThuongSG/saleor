import graphene
from graphene import relay

from ...core.permissions import PagePermissions, has_one_of_permissions
from ...menu import models
from ..channel.dataloaders import ChannelBySlugLoader
from ..channel.types import (
    ChannelContext,
    ChannelContextType,
    ChannelContextTypeWithMetadata,
)
from ..core.connection import CountableConnection
from ..core.types import ModelObjectType, NonNullList
from ..meta.types import ObjectWithMetadata
from ..page.dataloaders import PageByIdLoader
from ..page.types import Page
from ..translations.fields import TranslationField
from ..translations.types import MenuItemTranslation
from ..utils import get_user_or_app_from_context
from .dataloaders import (
    MenuByIdLoader,
    MenuItemByIdLoader,
    MenuItemChildrenLoader,
    MenuItemsByParentMenuLoader,
)


class Menu(ChannelContextTypeWithMetadata, ModelObjectType):
    id = graphene.GlobalID(required=True)
    name = graphene.String(required=True)
    slug = graphene.String(required=True)
    items = NonNullList(lambda: MenuItem)

    class Meta:
        default_resolver = ChannelContextType.resolver_with_context
        description = (
            "Represents a single menu - an object that is used to help navigate "
            "through the store."
        )
        interfaces = [relay.Node, ObjectWithMetadata]
        model = models.Menu

    @staticmethod
    def resolve_items(root: ChannelContext[models.Menu], info):
        menu_items = MenuItemsByParentMenuLoader(info.context).load(root.node.id)
        return menu_items.then(
            lambda menu_items: [
                ChannelContext(node=menu_item, channel_slug=root.channel_slug)
                for menu_item in menu_items
            ]
        )


class MenuCountableConnection(CountableConnection):
    class Meta:
        node = Menu


class MenuItem(ChannelContextTypeWithMetadata, ModelObjectType):
    id = graphene.GlobalID(required=True)
    name = graphene.String(required=True)
    menu = graphene.Field(Menu, required=True)
    parent = graphene.Field(lambda: MenuItem)    
    page = graphene.Field(
        Page,
        description=(
            "A page associated with this menu item. Requires one of the following "
            f"permissions to include unpublished items: "
            f"{PagePermissions.MANAGE_PAGES.name}."
        ),
    )
    level = graphene.Int(required=True)
    children = NonNullList(lambda: MenuItem)
    url = graphene.String(description="URL to the menu item.")
    translation = TranslationField(
        MenuItemTranslation,
        type_name="menu item",
        resolver=ChannelContextType.resolve_translation,
    )

    class Meta:
        default_resolver = ChannelContextType.resolver_with_context
        description = (
            "Represents a single item of the related menu. Can store categories, "
            "collection or pages."
        )
        interfaces = [relay.Node, ObjectWithMetadata]
        model = models.MenuItem


    @staticmethod
    def resolve_children(root: ChannelContext[models.MenuItem], info):
        menus = MenuItemChildrenLoader(info.context).load(root.node.id)
        return menus.then(
            lambda menus: [
                ChannelContext(node=menu, channel_slug=root.channel_slug)
                for menu in menus
            ]
        )


    @staticmethod
    def resolve_menu(root: ChannelContext[models.MenuItem], info):
        if root.node.menu_id:
            menu = MenuByIdLoader(info.context).load(root.node.menu_id)
            return menu.then(
                lambda menu: ChannelContext(node=menu, channel_slug=root.channel_slug)
            )
        return None

    @staticmethod
    def resolve_parent(root: ChannelContext[models.MenuItem], info):
        if root.node.parent_id:
            menu = MenuItemByIdLoader(info.context).load(root.node.parent_id)
            return menu.then(
                lambda menu: ChannelContext(node=menu, channel_slug=root.channel_slug)
            )
        return None

    @staticmethod
    def resolve_page(root: ChannelContext[models.MenuItem], info):
        if root.node.page_id:
            requestor = get_user_or_app_from_context(info.context)
            requestor_has_access_to_all = requestor.is_active and requestor.has_perm(
                PagePermissions.MANAGE_PAGES
            )
            return (
                PageByIdLoader(info.context)
                .load(root.node.page_id)
                .then(
                    lambda page: page
                    if requestor_has_access_to_all or page.is_visible
                    else None
                )
            )
        return None


class MenuItemCountableConnection(CountableConnection):
    class Meta:
        node = MenuItem


class MenuItemMoveInput(graphene.InputObjectType):
    item_id = graphene.ID(description="The menu item ID to move.", required=True)
    parent_id = graphene.ID(
        description="ID of the parent menu. If empty, menu will be top level menu."
    )
    sort_order = graphene.Int(
        description=(
            "The new relative sorting position of the item (from -inf to +inf). "
            "1 moves the item one position forward, -1 moves the item one position "
            "backward, 0 leaves the item unchanged."
        )
    )
