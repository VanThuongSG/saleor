import graphene
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from graphene import AbstractType, ObjectType, Union
from rx import Observable

from ... import __version__
from ...account.models import User
from ...core.prices import quantize_price
from ...menu.models import MenuItemTranslation
from ...page.models import PageTranslation
from ...post.models import PostTranslation
from ...webhook.event_types import WebhookEventAsyncType, WebhookEventSyncType
from ..account.types import User as UserType
from ..app.types import App as AppType
from ..channel import ChannelContext
from ..channel.dataloaders import ChannelByIdLoader
from ..core.descriptions import (
    ADDED_IN_32,
    ADDED_IN_34,
    ADDED_IN_35,
    ADDED_IN_36,
    PREVIEW_FEATURE,
)
from ..core.scalars import PositiveDecimal
from ..core.types import NonNullList
from ..translations import types as translation_types

TRANSLATIONS_TYPES_MAP = {
    PageTranslation: translation_types.PageTranslation,
    PostTranslation: translation_types.PostTranslation,
    MenuItemTranslation: translation_types.MenuItemTranslation,
}


class IssuingPrincipal(Union):
    class Meta:
        types = (AppType, UserType)

    @classmethod
    def resolve_type(cls, instance, info):
        if isinstance(instance, User):
            return UserType
        return AppType


class Event(graphene.Interface):
    issued_at = graphene.DateTime(description="Time of the event.")
    version = graphene.String(description="Saleor version that triggered the event.")
    issuing_principal = graphene.Field(
        IssuingPrincipal,
        description="The user or application that triggered the event.",
    )
    recipient = graphene.Field(
        "cms.graphql.app.types.App",
        description="The application receiving the webhook.",
    )

    @classmethod
    def get_type(cls, object_type: str):
        types = {
            WebhookEventAsyncType.ADDRESS_CREATED: AddressCreated,
            WebhookEventAsyncType.ADDRESS_UPDATED: AddressUpdated,
            WebhookEventAsyncType.ADDRESS_DELETED: AddressDeleted,
            WebhookEventAsyncType.APP_INSTALLED: AppInstalled,
            WebhookEventAsyncType.APP_UPDATED: AppUpdated,
            WebhookEventAsyncType.APP_DELETED: AppDeleted,
            WebhookEventAsyncType.APP_STATUS_CHANGED: AppStatusChanged,
            WebhookEventAsyncType.CHANNEL_CREATED: ChannelCreated,
            WebhookEventAsyncType.CHANNEL_UPDATED: ChannelUpdated,
            WebhookEventAsyncType.CHANNEL_DELETED: ChannelDeleted,
            WebhookEventAsyncType.CHANNEL_STATUS_CHANGED: ChannelStatusChanged,
            WebhookEventAsyncType.MENU_CREATED: MenuCreated,
            WebhookEventAsyncType.MENU_UPDATED: MenuUpdated,
            WebhookEventAsyncType.MENU_DELETED: MenuDeleted,
            WebhookEventAsyncType.MENU_ITEM_CREATED: MenuItemCreated,
            WebhookEventAsyncType.MENU_ITEM_UPDATED: MenuItemUpdated,
            WebhookEventAsyncType.MENU_ITEM_DELETED: MenuItemDeleted,
            WebhookEventAsyncType.CUSTOMER_CREATED: CustomerCreated,
            WebhookEventAsyncType.CUSTOMER_UPDATED: CustomerUpdated,
            WebhookEventAsyncType.PAGE_CREATED: PageCreated,
            WebhookEventAsyncType.PAGE_UPDATED: PageUpdated,
            WebhookEventAsyncType.PAGE_DELETED: PageDeleted,
            WebhookEventAsyncType.PAGE_TYPE_CREATED: PageTypeCreated,
            WebhookEventAsyncType.PAGE_TYPE_UPDATED: PageTypeUpdated,
            WebhookEventAsyncType.PAGE_TYPE_DELETED: PageTypeDeleted,
            WebhookEventAsyncType.POST_CREATED: PostCreated,
            WebhookEventAsyncType.POST_UPDATED: PostUpdated,
            WebhookEventAsyncType.POST_DELETED: PostDeleted,
            WebhookEventAsyncType.POST_TYPE_CREATED: PostTypeCreated,
            WebhookEventAsyncType.POST_TYPE_UPDATED: PostTypeUpdated,
            WebhookEventAsyncType.POST_TYPE_DELETED: PostTypeDeleted,
            WebhookEventAsyncType.PERMISSION_GROUP_CREATED: PermissionGroupCreated,
            WebhookEventAsyncType.PERMISSION_GROUP_UPDATED: PermissionGroupUpdated,
            WebhookEventAsyncType.PERMISSION_GROUP_DELETED: PermissionGroupDeleted,
            WebhookEventAsyncType.STAFF_CREATED: StaffCreated,
            WebhookEventAsyncType.STAFF_UPDATED: StaffUpdated,
            WebhookEventAsyncType.STAFF_DELETED: StaffDeleted,
        }
        return types.get(object_type)

    @classmethod
    def resolve_type(cls, instance, info):
        type_str, _ = instance
        return cls.get_type(type_str)

    @staticmethod
    def resolve_issued_at(_root, _info):
        return timezone.now()

    @staticmethod
    def resolve_version(_root, _info):
        return __version__

    @staticmethod
    def resolve_recipient(_root, info):
        return info.context.app

    @staticmethod
    def resolve_issuing_principal(_root, info):
        if isinstance(info.context.requestor, AnonymousUser):
            return None
        return info.context.requestor


class AddressBase(AbstractType):
    address = graphene.Field(
        "cms.graphql.account.types.Address",
        description="The address the event relates to.",
    )

    @staticmethod
    def resolve_address(root, _info):
        _, address = root
        return address


class AddressCreated(ObjectType, AddressBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when new address is created." + ADDED_IN_35 + PREVIEW_FEATURE
        )


class AddressUpdated(ObjectType, AddressBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when address is updated." + ADDED_IN_35 + PREVIEW_FEATURE
        )


class AddressDeleted(ObjectType, AddressBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when address is deleted." + ADDED_IN_35 + PREVIEW_FEATURE
        )


class AppBase(AbstractType):
    app = graphene.Field(
        "cms.graphql.app.types.App",
        description="The application the event relates to.",
    )

    @staticmethod
    def resolve_app(root, _info):
        _, app = root
        return app


class AppInstalled(ObjectType, AppBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when new app is installed." + ADDED_IN_34 + PREVIEW_FEATURE
        )


class AppUpdated(ObjectType, AppBase):
    class Meta:
        interfaces = (Event,)
        description = "Event sent when app is updated." + ADDED_IN_34 + PREVIEW_FEATURE


class AppDeleted(ObjectType, AppBase):
    class Meta:
        interfaces = (Event,)
        description = "Event sent when app is deleted." + ADDED_IN_34 + PREVIEW_FEATURE


class AppStatusChanged(ObjectType, AppBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when app status has changed." + ADDED_IN_34 + PREVIEW_FEATURE
        )


class ChannelBase(AbstractType):
    channel = graphene.Field(
        "cms.graphql.channel.types.Channel",
        description="The channel the event relates to.",
    )

    @staticmethod
    def resolve_channel(root, info):
        _, channel = root
        return channel


class ChannelCreated(ObjectType, ChannelBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when new channel is created." + ADDED_IN_32 + PREVIEW_FEATURE
        )


class ChannelUpdated(ObjectType, ChannelBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when channel is updated." + ADDED_IN_32 + PREVIEW_FEATURE
        )


class ChannelDeleted(ObjectType, ChannelBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when channel is deleted." + ADDED_IN_32 + PREVIEW_FEATURE
        )


class ChannelStatusChanged(ObjectType, ChannelBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when channel status has changed."
            + ADDED_IN_32
            + PREVIEW_FEATURE
        )


class MenuBase(AbstractType):
    menu = graphene.Field(
        "cms.graphql.menu.types.Menu",
        channel=graphene.String(
            description="Slug of a channel for which the data should be returned."
        ),
        description="The menu the event relates to.",
    )

    @staticmethod
    def resolve_menu(root, info, channel=None):
        _, menu = root
        return ChannelContext(node=menu, channel_slug=channel)


class MenuCreated(ObjectType, MenuBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when new menu is created." + ADDED_IN_34 + PREVIEW_FEATURE
        )


class MenuUpdated(ObjectType, MenuBase):
    class Meta:
        interfaces = (Event,)
        description = "Event sent when menu is updated." + ADDED_IN_34 + PREVIEW_FEATURE


class MenuDeleted(ObjectType, MenuBase):
    class Meta:
        interfaces = (Event,)
        description = "Event sent when menu is deleted." + ADDED_IN_34 + PREVIEW_FEATURE


class MenuItemBase(AbstractType):
    menu_item = graphene.Field(
        "cms.graphql.menu.types.MenuItem",
        channel=graphene.String(
            description="Slug of a channel for which the data should be returned."
        ),
        description="The menu item the event relates to.",
    )

    @staticmethod
    def resolve_menu_item(root, info, channel=None):
        _, menu_item = root
        return ChannelContext(node=menu_item, channel_slug=channel)


class MenuItemCreated(ObjectType, MenuItemBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when new menu item is created." + ADDED_IN_34 + PREVIEW_FEATURE
        )


class MenuItemUpdated(ObjectType, MenuItemBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when menu item is updated." + ADDED_IN_34 + PREVIEW_FEATURE
        )


class MenuItemDeleted(ObjectType, MenuItemBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when menu item is deleted." + ADDED_IN_34 + PREVIEW_FEATURE
        )


class UserBase(AbstractType):
    user = graphene.Field(
        "cms.graphql.account.types.User",
        description="The user the event relates to.",
    )

    @staticmethod
    def resolve_user(root, _info):
        _, user = root
        return user


class CustomerCreated(ObjectType, UserBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when new customer user is created."
            + ADDED_IN_32
            + PREVIEW_FEATURE
        )


class CustomerUpdated(ObjectType, UserBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when customer user is updated." + ADDED_IN_32 + PREVIEW_FEATURE
        )


class PageBase(AbstractType):
    page = graphene.Field(
        "cms.graphql.page.types.Page", description="The page the event relates to."
    )

    @staticmethod
    def resolve_page(root, _info):
        _, page = root
        return page


class PageCreated(ObjectType, PageBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when new page is created." + ADDED_IN_32 + PREVIEW_FEATURE
        )


class PageUpdated(ObjectType, PageBase):
    class Meta:
        interfaces = (Event,)
        description = "Event sent when page is updated." + ADDED_IN_32 + PREVIEW_FEATURE


class PageDeleted(ObjectType, PageBase):
    class Meta:
        interfaces = (Event,)
        description = "Event sent when page is deleted." + ADDED_IN_32 + PREVIEW_FEATURE


class PageTypeBase(AbstractType):
    page_type = graphene.Field(
        "cms.graphql.page.types.PageType",
        description="The page type the event relates to.",
    )

    @staticmethod
    def resolve_page_type(root, _info):
        _, page_type = root
        return page_type


class PageTypeCreated(ObjectType, PageTypeBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when new page type is created." + ADDED_IN_35 + PREVIEW_FEATURE
        )


class PageTypeUpdated(ObjectType, PageTypeBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when page type is updated." + ADDED_IN_35 + PREVIEW_FEATURE
        )


class PageTypeDeleted(ObjectType, PageTypeBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when page type is deleted." + ADDED_IN_35 + PREVIEW_FEATURE
        )


class PostBase(AbstractType):
    post = graphene.Field(
        "cms.graphql.post.types.Post", description="The post the event relates to."
    )

    @staticmethod
    def resolve_post(root, _info):
        _, post = root
        return post


class PostCreated(ObjectType, PostBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when new post is created." + ADDED_IN_32 + PREVIEW_FEATURE
        )


class PostUpdated(ObjectType, PostBase):
    class Meta:
        interfaces = (Event,)
        description = "Event sent when post is updated." + ADDED_IN_32 + PREVIEW_FEATURE


class PostDeleted(ObjectType, PostBase):
    class Meta:
        interfaces = (Event,)
        description = "Event sent when post is deleted." + ADDED_IN_32 + PREVIEW_FEATURE


class PostTypeBase(AbstractType):
    post_type = graphene.Field(
        "cms.graphql.post.types.PostType",
        description="The post type the event relates to.",
    )

    @staticmethod
    def resolve_post_type(root, _info):
        _, post_type = root
        return post_type


class PostTypeCreated(ObjectType, PostTypeBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when new post type is created." + ADDED_IN_35 + PREVIEW_FEATURE
        )


class PostTypeUpdated(ObjectType, PostTypeBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when post type is updated." + ADDED_IN_35 + PREVIEW_FEATURE
        )


class PostTypeDeleted(ObjectType, PostTypeBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when post type is deleted." + ADDED_IN_35 + PREVIEW_FEATURE
        )


class PermissionGroupBase(AbstractType):
    permission_group = graphene.Field(
        "cms.graphql.account.types.Group",
        description="The permission group the event relates to.",
    )

    @staticmethod
    def resolve_permission_group(root, _info):
        _, permission_group = root
        return permission_group


class PermissionGroupCreated(ObjectType, PermissionGroupBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when new permission group is created."
            + ADDED_IN_36
            + PREVIEW_FEATURE
        )


class PermissionGroupUpdated(ObjectType, PermissionGroupBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when permission group is updated."
            + ADDED_IN_36
            + PREVIEW_FEATURE
        )


class PermissionGroupDeleted(ObjectType, PermissionGroupBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when permission group is deleted."
            + ADDED_IN_36
            + PREVIEW_FEATURE
        )


class ShippingPriceBase(AbstractType):
    shipping_method = graphene.Field(
        "cms.graphql.shipping.types.ShippingMethodType",
        channel=graphene.String(
            description="Slug of a channel for which the data should be returned."
        ),
        description="The shipping method the event relates to.",
    )
    shipping_zone = graphene.Field(
        "cms.graphql.shipping.types.ShippingZone",
        channel=graphene.String(
            description="Slug of a channel for which the data should be returned."
        ),
        description="The shipping zone the shipping method belongs to.",
    )

    @staticmethod
    def resolve_shipping_method(root, _info, channel=None):
        _, shipping_method = root
        return ChannelContext(node=shipping_method, channel_slug=channel)

    @staticmethod
    def resolve_shipping_zone(root, _info, channel=None):
        _, shipping_method = root
        return ChannelContext(node=shipping_method.shipping_zone, channel_slug=channel)


class StaffCreated(ObjectType, UserBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when new staff user is created." + ADDED_IN_35 + PREVIEW_FEATURE
        )


class StaffUpdated(ObjectType, UserBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when staff user is updated." + ADDED_IN_35 + PREVIEW_FEATURE
        )


class StaffDeleted(ObjectType, UserBase):
    class Meta:
        interfaces = (Event,)
        description = (
            "Event sent when staff user is deleted." + ADDED_IN_35 + PREVIEW_FEATURE
        )


class Subscription(ObjectType):
    event = graphene.Field(
        Event,
        description="Look up subscription event." + ADDED_IN_32 + PREVIEW_FEATURE,
    )

    @staticmethod
    def resolve_event(root, info):
        return Observable.from_([root])


# List of events is created because `Event` type was change from `Union` to `Interface`
# so all subscription events types need to be added manually to `Schema`.

SUBSCRIPTION_EVENTS_TYPES = [   
    AppInstalled,
    AppUpdated,
    AppDeleted,
    AppStatusChanged,   
    ChannelCreated,
    ChannelUpdated,
    ChannelDeleted,
    ChannelStatusChanged,
    MenuCreated,
    MenuUpdated,
    MenuDeleted,
    MenuItemCreated,
    MenuItemUpdated,
    MenuItemDeleted,    
    CustomerCreated,
    CustomerUpdated,
    PageCreated,
    PageUpdated,
    PageDeleted,
    PageTypeCreated,
    PageTypeUpdated,
    PageTypeDeleted,
    PostCreated,
    PostUpdated,
    PostDeleted,
    PostTypeCreated,
    PostTypeUpdated,
    PostTypeDeleted,
    PermissionGroupCreated,
    PermissionGroupUpdated,
    PermissionGroupDeleted,
    StaffCreated,
    StaffUpdated,
    StaffDeleted,    
]
