import json
import uuid
from collections import defaultdict
from dataclasses import asdict
from decimal import Decimal
from typing import TYPE_CHECKING, Any, DefaultDict, Dict, Iterable, List, Optional, Set

import graphene
from django.contrib.auth.models import AnonymousUser
from django.db.models import F, QuerySet, Sum
from django.utils import timezone
from graphene.utils.str_converters import to_camel_case

from .. import __version__
from ..account.models import User
from ..core.utils.anonymization import (
    generate_fake_user,
)
from ..core.utils.json_serializer import CustomJsonEncoder
from ..page.models import Page
from ..post.models import Post

from . import traced_payload_generator
from .event_types import WebhookEventAsyncType
from .payload_serializers import PayloadSerializer


if TYPE_CHECKING:
    from ..plugins.base_plugin import RequestorOrLazyObject


ADDRESS_FIELDS = (
    "first_name",
    "last_name",
    "company_name",
    "street_address_1",
    "street_address_2",
    "city",
    "city_area",
    "postal_code",
    "country",
    "country_area",
    "phone",
)

CHANNEL_FIELDS = ("slug", "currency_code")

ORDER_FIELDS = (
    "status",
    "origin",
    "shipping_method_name",
    "collection_point_name",
    "shipping_price_net_amount",
    "shipping_price_gross_amount",
    "shipping_tax_rate",
    "weight",
    "language_code",
    "private_metadata",
    "metadata",
    "total_net_amount",
    "total_gross_amount",
    "undiscounted_total_net_amount",
    "undiscounted_total_gross_amount",
)

ORDER_PRICE_FIELDS = (
    "shipping_price_net_amount",
    "shipping_price_gross_amount",
    "total_net_amount",
    "total_gross_amount",
    "undiscounted_total_net_amount",
    "undiscounted_total_gross_amount",
)


def generate_requestor(requestor: Optional["RequestorOrLazyObject"] = None):
    if not requestor:
        return {"id": None, "type": None}
    if isinstance(requestor, (User, AnonymousUser)):
        return {"id": graphene.Node.to_global_id("User", requestor.id), "type": "user"}
    return {"id": requestor.name, "type": "app"}  # type: ignore


def generate_meta(*, requestor_data: Dict[str, Any], camel_case=False, **kwargs):
    meta_result = {
        "issued_at": timezone.now().isoformat(),
        "version": __version__,
        "issuing_principal": requestor_data,
    }

    meta_result.update(kwargs)

    if camel_case:
        meta = {}
        for key, value in meta_result.items():
            meta[to_camel_case(key)] = value
    else:
        meta = meta_result

    return meta


@traced_payload_generator
def generate_customer_payload(
    customer: "User", requestor: Optional["RequestorOrLazyObject"] = None
):
    serializer = PayloadSerializer()
    data = serializer.serialize(
        [customer],
        fields=[
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "language_code",
            "private_metadata",
            "metadata",
        ],
        additional_fields={            
            "addresses": (
                lambda c: c.addresses.all(),
                ADDRESS_FIELDS,
            ),
        },
        extra_dict_data={
            "meta": generate_meta(requestor_data=generate_requestor(requestor))
        },
    )
    return data


PRODUCT_FIELDS = (
    "name",
    "description",
    "currency",
    "updated_at",
    "charge_taxes",
    "weight",
    "publication_date",
    "is_published",
    "private_metadata",
    "metadata",
)


@traced_payload_generator
def generate_page_payload(
    page: Page, requestor: Optional["RequestorOrLazyObject"] = None
):
    serializer = PayloadSerializer()
    page_fields = [
        "private_metadata",
        "metadata",
        "title",
        "content",
        "published_at",
        "is_published",
        "updated_at",
    ]
    page_payload = serializer.serialize(
        [page],
        fields=page_fields,
        extra_dict_data={
            "data": generate_meta(requestor_data=generate_requestor(requestor)),
            # deprecated in 3.3 - published_at should be used instead
            "publication_date": page.published_at,
        },
    )
    return page_payload


@traced_payload_generator
def generate_post_payload(
    post: Post, requestor: Optional["RequestorOrLazyObject"] = None
):
    serializer = PayloadSerializer()
    post_fields = [
        "private_metadata",
        "metadata",
        "title",
        "content",
        "published_at",
        "is_published",
        "updated_at",
    ]
    post_payload = serializer.serialize(
        [post],
        fields=post_fields,
        extra_dict_data={
            "data": generate_meta(requestor_data=generate_requestor(requestor)),
            # deprecated in 3.3 - published_at should be used instead
            "publication_date": post.published_at,
        },
    )
    return post_payload


def _get_sample_object(qs: QuerySet):
    """Return random object from query."""
    random_object = qs.order_by("?").first()
    return random_object


@traced_payload_generator
def generate_sample_payload(event_name: str) -> Optional[dict]:
    posts_events = [
        WebhookEventAsyncType.POST_CREATED,
        WebhookEventAsyncType.POST_DELETED,
        WebhookEventAsyncType.POST_UPDATED,
    ]
    pages_events = [
        WebhookEventAsyncType.PAGE_CREATED,
        WebhookEventAsyncType.PAGE_DELETED,
        WebhookEventAsyncType.PAGE_UPDATED,
    ]
    user_events = [
        WebhookEventAsyncType.CUSTOMER_CREATED,
        WebhookEventAsyncType.CUSTOMER_UPDATED,
    ]

    if event_name in user_events:
        user = generate_fake_user()
        payload = generate_customer_payload(user)
    elif event_name in pages_events:
        page = _get_sample_object(Page.objects.all())
        if page:
            payload = generate_page_payload(page)
    elif event_name in posts_events:
        post = _get_sample_object(Post.objects.all())
        if post:
            payload = generate_post_payload(post)
    return json.loads(payload) if payload else None


def process_translation_context(context):
    additional_id_fields = [
        ("page_id", "Page"),
        ("page_type_id", "PageType"),
        ("post_id", "Post"),
        ("post_type_id", "PostType"),
    ]
    result = {}
    for key, type_name in additional_id_fields:
        if object_id := context.get(key, None):
            result[key] = graphene.Node.to_global_id(type_name, object_id)
        else:
            result[key] = None
    return result


