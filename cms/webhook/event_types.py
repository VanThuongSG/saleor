from ..core.permissions import (
    AccountPermissions,
    AppPermission,
    ChannelPermissions,   
    MenuPermissions,
    PagePermissions,
    PageTypePermissions,
    PostPermissions,
    PostTypePermissions,
    SitePermissions,
    
)


class WebhookEventAsyncType:
    ANY = "any_events"

    ADDRESS_CREATED = "address_created"
    ADDRESS_UPDATED = "address_updated"
    ADDRESS_DELETED = "address_deleted"

    APP_INSTALLED = "app_installed"
    APP_UPDATED = "app_updated"
    APP_DELETED = "app_deleted"
    APP_STATUS_CHANGED = "app_status_changed"

    CHANNEL_CREATED = "channel_created"
    CHANNEL_UPDATED = "channel_updated"
    CHANNEL_DELETED = "channel_deleted"
    CHANNEL_STATUS_CHANGED = "channel_status_changed"

    MENU_CREATED = "menu_created"
    MENU_UPDATED = "menu_updated"
    MENU_DELETED = "menu_deleted"
    MENU_ITEM_CREATED = "menu_item_created"
    MENU_ITEM_UPDATED = "menu_item_updated"
    MENU_ITEM_DELETED = "menu_item_deleted"
   
    CUSTOMER_CREATED = "customer_created"
    CUSTOMER_UPDATED = "customer_updated"
    CUSTOMER_DELETED = "customer_deleted"

    NOTIFY_USER = "notify_user"

    PAGE_CREATED = "page_created"
    PAGE_UPDATED = "page_updated"
    PAGE_DELETED = "page_deleted"

    PAGE_TYPE_CREATED = "page_type_created"
    PAGE_TYPE_UPDATED = "page_type_updated"
    PAGE_TYPE_DELETED = "page_type_deleted"

    POST_CREATED = "post_created"
    POST_UPDATED = "post_updated"
    POST_DELETED = "post_deleted"

    POST_TYPE_CREATED = "post_type_created"
    POST_TYPE_UPDATED = "post_type_updated"
    POST_TYPE_DELETED = "post_type_deleted"

    PERMISSION_GROUP_CREATED = "permission_group_created"
    PERMISSION_GROUP_UPDATED = "permission_group_updated"
    PERMISSION_GROUP_DELETED = "permission_group_deleted"

    STAFF_CREATED = "staff_created"
    STAFF_UPDATED = "staff_updated"
    STAFF_DELETED = "staff_deleted"

    TRANSACTION_ACTION_REQUEST = "transaction_action_request"

    TRANSLATION_CREATED = "translation_created"
    TRANSLATION_UPDATED = "translation_updated"

    OBSERVABILITY = "observability"

    DISPLAY_LABELS = {
        ANY: "Any events",
        ADDRESS_CREATED: "Address created",
        ADDRESS_UPDATED: "Address updated",
        ADDRESS_DELETED: "Address deleted",
        APP_INSTALLED: "App created",
        APP_UPDATED: "App updated",
        APP_DELETED: "App deleted",
        APP_STATUS_CHANGED: "App status changed",        
        CHANNEL_CREATED: "Channel created",
        CHANNEL_UPDATED: "Channel updated",
        CHANNEL_DELETED: "Channel deleted",
        CHANNEL_STATUS_CHANGED: "Channel status changed",        
        MENU_CREATED: "Menu created",
        MENU_UPDATED: "Menu updated",
        MENU_DELETED: "Menu deleted",
        MENU_ITEM_CREATED: "Menu item created",
        MENU_ITEM_UPDATED: "Menu item updated",
        MENU_ITEM_DELETED: "Menu item deleted",
        CUSTOMER_CREATED: "Customer created",
        CUSTOMER_UPDATED: "Customer updated",
        CUSTOMER_DELETED: "Customer deleted",
        
        NOTIFY_USER: "Notify user",
        PAGE_CREATED: "Page Created",
        PAGE_UPDATED: "Page Updated",
        PAGE_DELETED: "Page Deleted",
        PAGE_TYPE_CREATED: "Page type created",
        PAGE_TYPE_UPDATED: "Page type updated",
        PAGE_TYPE_DELETED: "Page type deleted",

        POST_CREATED: "Post Created",
        POST_UPDATED: "Post Updated",
        POST_DELETED: "Post Deleted",
        POST_TYPE_CREATED: "Post type created",
        POST_TYPE_UPDATED: "Post type updated",
        POST_TYPE_DELETED: "Post type deleted",


        PERMISSION_GROUP_CREATED: "Permission group created",
        PERMISSION_GROUP_UPDATED: "Permission group updated",
        PERMISSION_GROUP_DELETED: "Permission group deleted",
        STAFF_CREATED: "Staff created",
        STAFF_UPDATED: "Staff updated",
        STAFF_DELETED: "Staff deleted",
        OBSERVABILITY: "Observability",
    }

    CHOICES = [
        (ANY, DISPLAY_LABELS[ANY]),
        (ADDRESS_CREATED, DISPLAY_LABELS[ADDRESS_CREATED]),
        (ADDRESS_UPDATED, DISPLAY_LABELS[ADDRESS_UPDATED]),
        (ADDRESS_DELETED, DISPLAY_LABELS[ADDRESS_DELETED]),
        (APP_INSTALLED, DISPLAY_LABELS[APP_INSTALLED]),
        (APP_UPDATED, DISPLAY_LABELS[APP_UPDATED]),
        (APP_DELETED, DISPLAY_LABELS[APP_DELETED]),
        (APP_STATUS_CHANGED, DISPLAY_LABELS[APP_STATUS_CHANGED]),
        (CHANNEL_CREATED, DISPLAY_LABELS[CHANNEL_CREATED]),
        (CHANNEL_UPDATED, DISPLAY_LABELS[CHANNEL_UPDATED]),
        (CHANNEL_DELETED, DISPLAY_LABELS[CHANNEL_DELETED]),
        (CHANNEL_STATUS_CHANGED, DISPLAY_LABELS[CHANNEL_STATUS_CHANGED]),
        (MENU_CREATED, DISPLAY_LABELS[MENU_CREATED]),
        (MENU_UPDATED, DISPLAY_LABELS[MENU_UPDATED]),
        (MENU_DELETED, DISPLAY_LABELS[MENU_DELETED]),
        (MENU_ITEM_CREATED, DISPLAY_LABELS[MENU_ITEM_CREATED]),
        (MENU_ITEM_UPDATED, DISPLAY_LABELS[MENU_ITEM_UPDATED]),
        (MENU_ITEM_DELETED, DISPLAY_LABELS[MENU_ITEM_DELETED]),
        (CUSTOMER_CREATED, DISPLAY_LABELS[CUSTOMER_CREATED]),
        (CUSTOMER_UPDATED, DISPLAY_LABELS[CUSTOMER_UPDATED]),
        (CUSTOMER_DELETED, DISPLAY_LABELS[CUSTOMER_DELETED]),
        (NOTIFY_USER, DISPLAY_LABELS[NOTIFY_USER]),
        (PAGE_CREATED, DISPLAY_LABELS[PAGE_CREATED]),
        (PAGE_UPDATED, DISPLAY_LABELS[PAGE_UPDATED]),
        (PAGE_DELETED, DISPLAY_LABELS[PAGE_DELETED]),
        (PAGE_TYPE_CREATED, DISPLAY_LABELS[PAGE_TYPE_CREATED]),
        (PAGE_TYPE_UPDATED, DISPLAY_LABELS[PAGE_TYPE_UPDATED]),
        (PAGE_TYPE_DELETED, DISPLAY_LABELS[PAGE_TYPE_DELETED]),

        (POST_CREATED, DISPLAY_LABELS[POST_CREATED]),
        (POST_UPDATED, DISPLAY_LABELS[POST_UPDATED]),
        (POST_DELETED, DISPLAY_LABELS[POST_DELETED]),
        (POST_TYPE_CREATED, DISPLAY_LABELS[POST_TYPE_CREATED]),
        (POST_TYPE_UPDATED, DISPLAY_LABELS[POST_TYPE_UPDATED]),
        (POST_TYPE_DELETED, DISPLAY_LABELS[POST_TYPE_DELETED]),

        (PERMISSION_GROUP_CREATED, DISPLAY_LABELS[PERMISSION_GROUP_CREATED]),
        (PERMISSION_GROUP_UPDATED, DISPLAY_LABELS[PERMISSION_GROUP_UPDATED]),
        (PERMISSION_GROUP_DELETED, DISPLAY_LABELS[PERMISSION_GROUP_DELETED]),
        (STAFF_CREATED, DISPLAY_LABELS[STAFF_CREATED]),
        (STAFF_UPDATED, DISPLAY_LABELS[STAFF_UPDATED]),
        (STAFF_DELETED, DISPLAY_LABELS[STAFF_DELETED]),
        (OBSERVABILITY, DISPLAY_LABELS[OBSERVABILITY]),
    ]

    ALL = [event[0] for event in CHOICES]

    PERMISSIONS = {
        ADDRESS_CREATED: AccountPermissions.MANAGE_USERS,
        ADDRESS_UPDATED: AccountPermissions.MANAGE_USERS,
        ADDRESS_DELETED: AccountPermissions.MANAGE_USERS,
        APP_INSTALLED: AppPermission.MANAGE_APPS,
        APP_UPDATED: AppPermission.MANAGE_APPS,
        APP_DELETED: AppPermission.MANAGE_APPS,
        APP_STATUS_CHANGED: AppPermission.MANAGE_APPS,
        
        CHANNEL_CREATED: ChannelPermissions.MANAGE_CHANNELS,
        CHANNEL_UPDATED: ChannelPermissions.MANAGE_CHANNELS,
        CHANNEL_DELETED: ChannelPermissions.MANAGE_CHANNELS,
        CHANNEL_STATUS_CHANGED: ChannelPermissions.MANAGE_CHANNELS,
        MENU_CREATED: MenuPermissions.MANAGE_MENUS,
        MENU_UPDATED: MenuPermissions.MANAGE_MENUS,
        MENU_DELETED: MenuPermissions.MANAGE_MENUS,
        MENU_ITEM_CREATED: MenuPermissions.MANAGE_MENUS,
        MENU_ITEM_UPDATED: MenuPermissions.MANAGE_MENUS,
        MENU_ITEM_DELETED: MenuPermissions.MANAGE_MENUS,
        CUSTOMER_CREATED: AccountPermissions.MANAGE_USERS,
        CUSTOMER_UPDATED: AccountPermissions.MANAGE_USERS,
        CUSTOMER_DELETED: AccountPermissions.MANAGE_USERS,
        NOTIFY_USER: AccountPermissions.MANAGE_USERS,
        PAGE_CREATED: PagePermissions.MANAGE_PAGES,
        PAGE_UPDATED: PagePermissions.MANAGE_PAGES,
        PAGE_DELETED: PagePermissions.MANAGE_PAGES,
        PAGE_TYPE_CREATED: PageTypePermissions.MANAGE_PAGE_TYPES_AND_ATTRIBUTES,
        PAGE_TYPE_UPDATED: PageTypePermissions.MANAGE_PAGE_TYPES_AND_ATTRIBUTES,
        PAGE_TYPE_DELETED: PageTypePermissions.MANAGE_PAGE_TYPES_AND_ATTRIBUTES,

        POST_CREATED: PostPermissions.MANAGE_POSTS,
        POST_UPDATED: PostPermissions.MANAGE_POSTS,
        POST_DELETED: PostPermissions.MANAGE_POSTS,
        POST_TYPE_CREATED: PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES,
        POST_TYPE_UPDATED: PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES,
        POST_TYPE_DELETED: PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES,

        PERMISSION_GROUP_CREATED: AccountPermissions.MANAGE_STAFF,
        PERMISSION_GROUP_UPDATED: AccountPermissions.MANAGE_STAFF,
        PERMISSION_GROUP_DELETED: AccountPermissions.MANAGE_STAFF,
        STAFF_CREATED: AccountPermissions.MANAGE_STAFF,
        STAFF_UPDATED: AccountPermissions.MANAGE_STAFF,
        STAFF_DELETED: AccountPermissions.MANAGE_STAFF,
        TRANSLATION_CREATED: SitePermissions.MANAGE_TRANSLATIONS,
        TRANSLATION_UPDATED: SitePermissions.MANAGE_TRANSLATIONS,
        OBSERVABILITY: AppPermission.MANAGE_OBSERVABILITY,
    }


class WebhookEventSyncType:

    DISPLAY_LABELS = {
    }

    CHOICES = [
    ]

    ALL = [event[0] for event in CHOICES]

    PAYMENT_EVENTS = [
    ]

    PERMISSIONS = {
    }


SUBSCRIBABLE_EVENTS = [
    WebhookEventAsyncType.ADDRESS_CREATED,
    WebhookEventAsyncType.ADDRESS_UPDATED,
    WebhookEventAsyncType.ADDRESS_DELETED,
    WebhookEventAsyncType.APP_INSTALLED,
    WebhookEventAsyncType.APP_UPDATED,
    WebhookEventAsyncType.APP_DELETED,
    WebhookEventAsyncType.APP_STATUS_CHANGED,
    WebhookEventAsyncType.CHANNEL_CREATED,
    WebhookEventAsyncType.CHANNEL_UPDATED,
    WebhookEventAsyncType.CHANNEL_DELETED,
    WebhookEventAsyncType.CHANNEL_STATUS_CHANGED,
    WebhookEventAsyncType.MENU_CREATED,
    WebhookEventAsyncType.MENU_UPDATED,
    WebhookEventAsyncType.MENU_DELETED,
    WebhookEventAsyncType.MENU_ITEM_CREATED,
    WebhookEventAsyncType.MENU_ITEM_UPDATED,
    WebhookEventAsyncType.MENU_ITEM_DELETED,
    WebhookEventAsyncType.CUSTOMER_CREATED,
    WebhookEventAsyncType.CUSTOMER_UPDATED,
    WebhookEventAsyncType.CUSTOMER_DELETED,
    WebhookEventAsyncType.PAGE_CREATED,
    WebhookEventAsyncType.PAGE_UPDATED,
    WebhookEventAsyncType.PAGE_DELETED,
    WebhookEventAsyncType.PAGE_TYPE_CREATED,
    WebhookEventAsyncType.PAGE_TYPE_UPDATED,
    WebhookEventAsyncType.PAGE_TYPE_DELETED,    
    WebhookEventAsyncType.POST_CREATED,
    WebhookEventAsyncType.POST_UPDATED,
    WebhookEventAsyncType.POST_DELETED,
    WebhookEventAsyncType.POST_TYPE_CREATED,
    WebhookEventAsyncType.POST_TYPE_UPDATED,
    WebhookEventAsyncType.POST_TYPE_DELETED,
    WebhookEventAsyncType.PERMISSION_GROUP_CREATED,
    WebhookEventAsyncType.PERMISSION_GROUP_UPDATED,
    WebhookEventAsyncType.PERMISSION_GROUP_DELETED,
    WebhookEventAsyncType.STAFF_CREATED,
    WebhookEventAsyncType.STAFF_UPDATED,
    WebhookEventAsyncType.STAFF_DELETED,
    WebhookEventAsyncType.TRANSACTION_ACTION_REQUEST,
    WebhookEventAsyncType.TRANSLATION_CREATED,
    WebhookEventAsyncType.TRANSLATION_UPDATED,
]
