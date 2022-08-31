import decimal
import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from time import time
from typing import TYPE_CHECKING, Any, List, Optional

from django.db.models import QuerySet

from ...app.models import App
from ...core.models import (
    EventDelivery,
    EventDeliveryAttempt,
    EventDeliveryStatus,
    EventPayload,
)

from ...webhook.event_types import WebhookEventSyncType

if TYPE_CHECKING:
    from .tasks import WebhookResponse

APP_GATEWAY_ID_PREFIX = "app"

APP_ID_PREFIX = "app"

logger = logging.getLogger(__name__)


@dataclass
class PaymentAppData:
    app_pk: int
    name: str


@dataclass
class ShippingAppData:
    app_pk: int
    shipping_method_id: str


@contextmanager
def catch_duration_time():
    start = time()
    yield lambda: time() - start


def create_event_delivery_list_for_webhooks(
    webhooks: QuerySet,
    event_payload: "EventPayload",
    event_type: str,
) -> List[EventDelivery]:
    event_deliveries = EventDelivery.objects.bulk_create(
        [
            EventDelivery(
                status=EventDeliveryStatus.PENDING,
                event_type=event_type,
                payload=event_payload,
                webhook=webhook,
            )
            for webhook in webhooks
        ]
    )
    return event_deliveries


def create_attempt(
    delivery: "EventDelivery",
    task_id: str = None,
):
    attempt = EventDeliveryAttempt.objects.create(
        delivery=delivery,
        task_id=task_id,
        duration=None,
        response=None,
        request_headers=None,
        response_headers=None,
        status=EventDeliveryStatus.PENDING,
    )
    return attempt


def attempt_update(
    attempt: "EventDeliveryAttempt",
    webhook_response: "WebhookResponse",
):

    attempt.duration = webhook_response.duration
    attempt.response = webhook_response.content
    attempt.response_headers = json.dumps(webhook_response.response_headers)
    attempt.response_status_code = webhook_response.response_status_code
    attempt.request_headers = json.dumps(webhook_response.request_headers)
    attempt.status = webhook_response.status
    attempt.save(
        update_fields=[
            "duration",
            "response",
            "response_headers",
            "response_status_code",
            "request_headers",
            "status",
        ]
    )


def delivery_update(delivery: "EventDelivery", status: str):
    delivery.status = status
    delivery.save(update_fields=["status"])


def clear_successful_delivery(delivery: "EventDelivery"):
    if delivery.status == EventDeliveryStatus.SUCCESS:
        payload_id = delivery.payload_id
        delivery.delete()
        if payload_id:
            EventPayload.objects.filter(pk=payload_id, deliveries__isnull=True).delete()


DEFAULT_TAX_CODE = "UNMAPPED"
DEFAULT_TAX_DESCRIPTION = "Unmapped Product/Product Type"


def get_meta_code_key(app: App) -> str:
    return f"{app.identifier}.code"


def get_meta_description_key(app: App) -> str:
    return f"{app.identifier}.description"
