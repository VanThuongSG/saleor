import graphene

from ...webhook.event_types import WebhookEventAsyncType, WebhookEventSyncType
from ..core.descriptions import ADDED_IN_36, PREVIEW_FEATURE
from ..core.utils import str_to_enum

checkout_updated_event_enum_description = (
    "A checkout is updated. It also triggers all updates related to the checkout."
)

order_confirmed_event_enum_description = (
    "An order is confirmed (status change unconfirmed -> unfulfilled) "
    "by a staff user using the OrderConfirm mutation. "
    "It also triggers when the user completes the checkout and the shop "
    "setting `automatically_confirm_all_new_orders` is enabled."
)

order_fully_paid_event_enum_description = "Payment is made and an order is fully paid."

order_updated_event_enum_description = (
    "An order is updated; triggered for all changes related to an order; "
    "covers all other order webhooks, except for ORDER_CREATED."
)


WEBHOOK_EVENT_DESCRIPTION = {
    WebhookEventAsyncType.ADDRESS_CREATED: "A new address created.",
    WebhookEventAsyncType.ADDRESS_UPDATED: "An address updated.",
    WebhookEventAsyncType.ADDRESS_DELETED: "An address deleted.",
    WebhookEventAsyncType.APP_INSTALLED: "A new app installed.",
    WebhookEventAsyncType.APP_UPDATED: "An app updated.",
    WebhookEventAsyncType.APP_DELETED: "An app deleted.",
    WebhookEventAsyncType.APP_STATUS_CHANGED: "An app status is changed.",
    WebhookEventAsyncType.CHANNEL_CREATED: "A new channel created.",
    WebhookEventAsyncType.CHANNEL_UPDATED: "A channel is updated.",
    WebhookEventAsyncType.CHANNEL_DELETED: "A channel is deleted.",
    WebhookEventAsyncType.CHANNEL_STATUS_CHANGED: "A channel status is changed.",
    WebhookEventAsyncType.CUSTOMER_CREATED: "A new customer account is created.",
    WebhookEventAsyncType.CUSTOMER_UPDATED: "A customer account is updated.",
    WebhookEventAsyncType.CUSTOMER_DELETED: "A customer account is deleted.",
    WebhookEventAsyncType.MENU_CREATED: "A new menu created.",
    WebhookEventAsyncType.MENU_UPDATED: "A menu is updated.",
    WebhookEventAsyncType.MENU_DELETED: "A menu is deleted.",
    WebhookEventAsyncType.MENU_ITEM_CREATED: "A new menu item created.",
    WebhookEventAsyncType.MENU_ITEM_UPDATED: "A menu item is updated.",
    WebhookEventAsyncType.MENU_ITEM_DELETED: "A menu item is deleted.",
    WebhookEventAsyncType.NOTIFY_USER: "User notification triggered.",
    WebhookEventAsyncType.PAGE_CREATED: "A new page is created.",
    WebhookEventAsyncType.PAGE_UPDATED: "A page is updated.",
    WebhookEventAsyncType.PAGE_DELETED: "A page is deleted.",
    WebhookEventAsyncType.PAGE_TYPE_CREATED: "A new page type is created.",
    WebhookEventAsyncType.PAGE_TYPE_UPDATED: "A page type is updated.",
    WebhookEventAsyncType.PAGE_TYPE_DELETED: "A page type is deleted.",
    WebhookEventAsyncType.POST_CREATED: "A new post is created.",
    WebhookEventAsyncType.POST_UPDATED: "A post is updated.",
    WebhookEventAsyncType.POST_DELETED: "A post is deleted.",
    WebhookEventAsyncType.POST_TYPE_CREATED: "A new post type is created.",
    WebhookEventAsyncType.POST_TYPE_UPDATED: "A post type is updated.",
    WebhookEventAsyncType.POST_TYPE_DELETED: "A post type is deleted.",
    WebhookEventAsyncType.PERMISSION_GROUP_CREATED: (
        "A new permission group is created."
    ),
    WebhookEventAsyncType.PERMISSION_GROUP_UPDATED: "A permission group is updated.",
    WebhookEventAsyncType.PERMISSION_GROUP_DELETED: "A permission group is deleted.",
    WebhookEventAsyncType.STAFF_CREATED: "A new staff user is created.",
    WebhookEventAsyncType.STAFF_UPDATED: "A staff user is updated.",
    WebhookEventAsyncType.STAFF_DELETED: "A staff user is deleted.",
    WebhookEventAsyncType.TRANSACTION_ACTION_REQUEST: (
        "An action requested for transaction."
    ),
    WebhookEventAsyncType.TRANSLATION_CREATED: "A new translation is created.",
    WebhookEventAsyncType.TRANSLATION_UPDATED: "A translation is updated.",
    WebhookEventAsyncType.ANY: "All the events.",
    WebhookEventAsyncType.OBSERVABILITY: "An observability event is created.",
}


def description(enum):
    if enum:
        return WEBHOOK_EVENT_DESCRIPTION.get(enum.value)
    return "Enum determining type of webhook."


WebhookEventTypeEnum = graphene.Enum(
    "WebhookEventTypeEnum",
    [
        (str_to_enum(e_type[0]), e_type[0])
        for e_type in (WebhookEventAsyncType.CHOICES + WebhookEventSyncType.CHOICES)
    ],
    description=description,
)


WebhookEventTypeAsyncEnum = graphene.Enum(
    "WebhookEventTypeAsyncEnum",
    [(str_to_enum(e_type[0]), e_type[0]) for e_type in WebhookEventAsyncType.CHOICES],
    description=description,
)

WebhookEventTypeSyncEnum = graphene.Enum(
    "WebhookEventTypeSyncEnum",
    [(str_to_enum(e_type[0]), e_type[0]) for e_type in WebhookEventSyncType.CHOICES],
    description=description,
)

WebhookSampleEventTypeEnum = graphene.Enum(
    "WebhookSampleEventTypeEnum",
    [
        (str_to_enum(e_type[0]), e_type[0])
        for e_type in WebhookEventAsyncType.CHOICES
        if e_type[0] != WebhookEventAsyncType.ANY
    ],
)


class EventDeliveryStatusEnum(graphene.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
