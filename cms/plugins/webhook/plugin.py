import json
import logging
from typing import TYPE_CHECKING, Any, DefaultDict, List, Optional, Set, Union

import graphene

from ...app.models import App
from ...core import EventDeliveryStatus
from ...core.models import EventDelivery
from ...core.notify_events import NotifyEventType
from ...core.utils.json_serializer import CustomJsonEncoder
from ...webhook.event_types import WebhookEventAsyncType
from ...webhook.payloads import (
    generate_customer_payload,
    generate_meta,
    generate_page_payload,
    generate_post_payload,
    generate_requestor,
)
from ...webhook.utils import get_webhooks_for_event
from ..base_plugin import BasePlugin
from .const import CACHE_EXCLUDED_SHIPPING_KEY
from .tasks import (
    send_webhook_request_async,
    trigger_webhooks_async,
)
from .utils import (
    delivery_update,
)

if TYPE_CHECKING:
    from ...account.models import Address, Group, User
    from ...channel.models import Channel
    from ...menu.models import Menu, MenuItem
    from ...page.models import Page, PageType
    from ...post.models import Post, PostType


logger = logging.getLogger(__name__)


class WebhookPlugin(BasePlugin):
    PLUGIN_ID = "mirumee.webhooks"
    PLUGIN_NAME = "Webhooks"
    DEFAULT_ACTIVE = True
    CONFIGURATION_PER_CHANNEL = False

    @classmethod
    def check_plugin_id(cls, plugin_id: str) -> bool:
        is_webhook_plugin = super().check_plugin_id(plugin_id)        
        return is_webhook_plugin

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active = True

    @staticmethod
    def _serialize_payload(data):
        return json.dumps(data, cls=CustomJsonEncoder)

    def _generate_meta(self):
        return generate_meta(requestor_data=generate_requestor(self.requestor))

    def _trigger_address_event(self, event_type, address):
        if webhooks := get_webhooks_for_event(event_type):
            payload = self._serialize_payload(
                {
                    "id": graphene.Node.to_global_id("Address", address.id),
                    "city": address.city,
                    "company_name": address.company_name,
                    "meta": self._generate_meta(),
                }
            )
            trigger_webhooks_async(
                payload, event_type, webhooks, address, self.requestor
            )

    def address_created(self, address: "Address", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self._trigger_address_event(WebhookEventAsyncType.ADDRESS_CREATED, address)

    def address_updated(self, address: "Address", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self._trigger_address_event(WebhookEventAsyncType.ADDRESS_UPDATED, address)

    def address_deleted(self, address: "Address", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self._trigger_address_event(WebhookEventAsyncType.ADDRESS_DELETED, address)

    def _trigger_app_event(self, event_type, app):
        if webhooks := get_webhooks_for_event(event_type):
            payload = self._serialize_payload(
                {
                    "id": graphene.Node.to_global_id("App", app.id),
                    "is_active": app.is_active,
                    "name": app.name,
                    "meta": self._generate_meta(),
                }
            )
            trigger_webhooks_async(payload, event_type, webhooks, app, self.requestor)

    def app_installed(self, app: "App", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self._trigger_app_event(WebhookEventAsyncType.APP_INSTALLED, app)

    def app_updated(self, app: "App", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self._trigger_app_event(WebhookEventAsyncType.APP_UPDATED, app)

    def app_deleted(self, app: "App", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self._trigger_app_event(WebhookEventAsyncType.APP_DELETED, app)

    def app_status_changed(self, app: "App", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self._trigger_app_event(WebhookEventAsyncType.APP_STATUS_CHANGED, app)
    
    def __trigger_channel_event(self, event_type, channel):
        if webhooks := get_webhooks_for_event(event_type):
            payload = self._serialize_payload(
                {
                    "id": graphene.Node.to_global_id("Channel", channel.id),
                    "is_active": channel.is_active,
                    "meta": self._generate_meta(),
                }
            )
            trigger_webhooks_async(
                payload, event_type, webhooks, channel, self.requestor
            )

    def channel_created(self, channel: "Channel", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self.__trigger_channel_event(WebhookEventAsyncType.CHANNEL_CREATED, channel)

    def channel_updated(self, channel: "Channel", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self.__trigger_channel_event(WebhookEventAsyncType.CHANNEL_UPDATED, channel)

    def channel_deleted(self, channel: "Channel", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self.__trigger_channel_event(WebhookEventAsyncType.CHANNEL_DELETED, channel)

    def channel_status_changed(self, channel: "Channel", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self.__trigger_channel_event(
            WebhookEventAsyncType.CHANNEL_STATUS_CHANGED, channel
        )
    
    def _trigger_menu_event(self, event_type, menu):
        if webhooks := get_webhooks_for_event(event_type):
            payload = self._serialize_payload(
                {
                    "id": graphene.Node.to_global_id("Menu", menu.id),
                    "slug": menu.slug,
                    "meta": self._generate_meta(),
                }
            )
            trigger_webhooks_async(payload, event_type, webhooks, menu, self.requestor)

    def menu_created(self, menu: "Menu", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self._trigger_menu_event(WebhookEventAsyncType.MENU_CREATED, menu)

    def menu_updated(self, menu: "Menu", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self._trigger_menu_event(WebhookEventAsyncType.MENU_UPDATED, menu)

    def menu_deleted(self, menu: "Menu", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self._trigger_menu_event(WebhookEventAsyncType.MENU_DELETED, menu)

    def __trigger_menu_item_event(self, event_type, menu_item):
        if webhooks := get_webhooks_for_event(event_type):
            payload = self._serialize_payload(
                {
                    "id": graphene.Node.to_global_id("MenuItem", menu_item.id),
                    "name": menu_item.name,
                    "menu": {
                        "id": graphene.Node.to_global_id("Menu", menu_item.menu_id)
                    },
                    "meta": self._generate_meta(),
                }
            )
            trigger_webhooks_async(
                payload, event_type, webhooks, menu_item, self.requestor
            )

    def menu_item_created(self, menu_item: "MenuItem", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self.__trigger_menu_item_event(
            WebhookEventAsyncType.MENU_ITEM_CREATED, menu_item
        )

    def menu_item_updated(self, menu_item: "MenuItem", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self.__trigger_menu_item_event(
            WebhookEventAsyncType.MENU_ITEM_UPDATED, menu_item
        )

    def menu_item_deleted(self, menu_item: "MenuItem", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self.__trigger_menu_item_event(
            WebhookEventAsyncType.MENU_ITEM_DELETED, menu_item
        )
    
    def customer_created(self, customer: "User", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        event_type = WebhookEventAsyncType.CUSTOMER_CREATED
        if webhooks := get_webhooks_for_event(event_type):
            customer_data = generate_customer_payload(customer, self.requestor)
            trigger_webhooks_async(
                customer_data, event_type, webhooks, customer, self.requestor
            )

    def customer_updated(self, customer: "User", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        event_type = WebhookEventAsyncType.CUSTOMER_UPDATED
        if webhooks := get_webhooks_for_event(event_type):
            customer_data = generate_customer_payload(customer, self.requestor)
            trigger_webhooks_async(
                customer_data, event_type, webhooks, customer, self.requestor
            )

    def customer_deleted(self, customer: "User", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        event_type = WebhookEventAsyncType.CUSTOMER_DELETED
        if webhooks := get_webhooks_for_event(event_type):
            customer_data = generate_customer_payload(customer, self.requestor)
            trigger_webhooks_async(
                customer_data, event_type, webhooks, customer, self.requestor
            )
    
    def notify(
        self, event: Union[NotifyEventType, str], payload: dict, previous_value
    ) -> Any:
        if not self.active:
            return previous_value
        event_type = WebhookEventAsyncType.NOTIFY_USER
        if webhooks := get_webhooks_for_event(event_type):
            data = self._serialize_payload(
                {
                    "notify_event": event,
                    "payload": payload,
                    "meta": generate_meta(
                        requestor_data=generate_requestor(self.requestor)
                    ),
                }
            )
            if event not in NotifyEventType.CHOICES:
                logger.info(f"Webhook {event_type} triggered for {event} notify event.")
            trigger_webhooks_async(data, event_type, webhooks)

    def page_created(self, page: "Page", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        event_type = WebhookEventAsyncType.PAGE_CREATED
        if webhooks := get_webhooks_for_event(event_type):
            page_data = generate_page_payload(page, self.requestor)
            trigger_webhooks_async(
                page_data, event_type, webhooks, page, self.requestor
            )

    def page_updated(self, page: "Page", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        event_type = WebhookEventAsyncType.PAGE_UPDATED
        if webhooks := get_webhooks_for_event(event_type):
            page_data = generate_page_payload(page, self.requestor)
            trigger_webhooks_async(
                page_data, event_type, webhooks, page, self.requestor
            )

    def page_deleted(self, page: "Page", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        event_type = WebhookEventAsyncType.PAGE_DELETED
        if webhooks := get_webhooks_for_event(event_type):
            page_data = generate_page_payload(page, self.requestor)
            trigger_webhooks_async(
                page_data, event_type, webhooks, page, self.requestor
            )
    
    def post_created(self, post: "Post", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        event_type = WebhookEventAsyncType.POST_CREATED
        if webhooks := get_webhooks_for_event(event_type):
            page_data = generate_page_payload(post, self.requestor)
            trigger_webhooks_async(
                page_data, event_type, webhooks, post, self.requestor
            )

    def post_updated(self, post: "Post", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        event_type = WebhookEventAsyncType.POST_UPDATED
        if webhooks := get_webhooks_for_event(event_type):
            post_data = generate_post_payload(post, self.requestor)
            trigger_webhooks_async(
                post_data, event_type, webhooks, post, self.requestor
            )

    def post_deleted(self, post: "Post", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        event_type = WebhookEventAsyncType.POST_DELETED
        if webhooks := get_webhooks_for_event(event_type):
            post_data = generate_post_payload(post, self.requestor)
            trigger_webhooks_async(
                post_data, event_type, webhooks, post, self.requestor
            )

    def _trigger_page_type_event(self, event_type, page_type):
        if webhooks := get_webhooks_for_event(event_type):
            payload = self._serialize_payload(
                {
                    "id": graphene.Node.to_global_id("PageType", page_type.id),
                    "name": page_type.name,
                    "slug": page_type.slug,
                    "meta": self._generate_meta(),
                }
            )
            trigger_webhooks_async(
                payload, event_type, webhooks, page_type, self.requestor
            )

    def page_type_created(self, page_type: "PageType", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        self._trigger_page_type_event(
            WebhookEventAsyncType.PAGE_TYPE_CREATED, page_type
        )

    def page_type_updated(self, page_type: "PageType", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        self._trigger_page_type_event(
            WebhookEventAsyncType.PAGE_TYPE_UPDATED, page_type
        )

    def page_type_deleted(self, page_type: "PageType", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        self._trigger_page_type_event(
            WebhookEventAsyncType.PAGE_TYPE_DELETED, page_type
        )

    def _trigger_post_type_event(self, event_type, post_type):
        if webhooks := get_webhooks_for_event(event_type):
            payload = self._serialize_payload(
                {
                    "id": graphene.Node.to_global_id("PostType", post_type.id),
                    "name": post_type.name,
                    "slug": post_type.slug,
                    "meta": self._generate_meta(),
                }
            )
            trigger_webhooks_async(
                payload, event_type, webhooks, post_type, self.requestor
            )

    def post_type_created(self, post_type: "PostType", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        self._trigger_post_type_event(
            WebhookEventAsyncType.POST_TYPE_CREATED, post_type
        )

    def post_type_updated(self, post_type: "PostType", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        self._trigger_post_type_event(
            WebhookEventAsyncType.PAGE_TYPE_UPDATED, post_type
        )

    def post_type_deleted(self, post_type: "PostType", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        self._trigger_post_type_event(
            WebhookEventAsyncType.POST_TYPE_DELETED, post_type
        )

    def _trigger_permission_group_event(self, event_type, group):
        if webhooks := get_webhooks_for_event(event_type):
            payload = self._serialize_payload(
                {
                    "id": graphene.Node.to_global_id("Group", group.id),
                    "meta": self._generate_meta(),
                }
            )
            trigger_webhooks_async(payload, event_type, webhooks, group, self.requestor)

    def permission_group_created(self, group: "Group", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        self._trigger_permission_group_event(
            WebhookEventAsyncType.PERMISSION_GROUP_CREATED, group
        )

    def permission_group_updated(self, group: "Group", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        self._trigger_permission_group_event(
            WebhookEventAsyncType.PERMISSION_GROUP_UPDATED, group
        )

    def permission_group_deleted(self, group: "Group", previous_value: Any) -> Any:
        if not self.active:
            return previous_value
        self._trigger_permission_group_event(
            WebhookEventAsyncType.PERMISSION_GROUP_DELETED, group
        )
    
    def _trigger_staff_event(self, event_type, staff_user):
        if webhooks := get_webhooks_for_event(event_type):
            payload = self._serialize_payload(
                {
                    "id": graphene.Node.to_global_id("User", staff_user.id),
                    "email": staff_user.email,
                    "meta": self._generate_meta(),
                }
            )
            trigger_webhooks_async(
                payload, event_type, webhooks, staff_user, self.requestor
            )

    def staff_created(self, staff_user: "User", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self._trigger_staff_event(WebhookEventAsyncType.STAFF_CREATED, staff_user)

    def staff_updated(self, staff_user: "User", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self._trigger_staff_event(WebhookEventAsyncType.STAFF_UPDATED, staff_user)

    def staff_deleted(self, staff_user: "User", previous_value: None) -> None:
        if not self.active:
            return previous_value
        self._trigger_staff_event(WebhookEventAsyncType.STAFF_DELETED, staff_user)
    
    def _trigger_voucher_event(self, event_type, voucher):
        if webhooks := get_webhooks_for_event(event_type):
            payload = self._serialize_payload(
                {
                    "id": graphene.Node.to_global_id("Voucher", voucher.id),
                    "name": voucher.name,
                    "code": voucher.code,
                    "meta": self._generate_meta(),
                }
            )
            trigger_webhooks_async(
                payload, event_type, webhooks, voucher, self.requestor
            )    

    def event_delivery_retry(self, delivery: "EventDelivery", previous_value: Any):
        if not self.active:
            return previous_value
        delivery_update(delivery, status=EventDeliveryStatus.PENDING)
        send_webhook_request_async.delay(delivery.pk)
