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
from ..core.utils import build_absolute_uri
from ..core.utils.anonymization import (
    generate_fake_user,
)
from ..core.utils.json_serializer import CustomJsonEncoder
from ..page.models import Page
from ..post.models import Post
from ..plugins.webhook.utils import from_payment_app_id
from ..product import ProductMediaTypes
from ..product.models import Collection, Product
from ..shipping.interface import ShippingMethodData
from ..warehouse.models import Stock, Warehouse
from . import traced_payload_generator
from .event_types import WebhookEventAsyncType
from .payload_serializers import PayloadSerializer
from .serializers import (
    serialize_checkout_lines,
    serialize_checkout_lines_for_tax_calculation,
    serialize_product_or_variant_attributes,
)
from .utils import get_base_price


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


def prepare_order_lines_allocations_payload(line):
    warehouse_id_quantity_allocated_map = list(
        line.allocations.values(  # type: ignore
            "quantity_allocated",
            warehouse_id=F("stock__warehouse_id"),
        )
    )
    for item in warehouse_id_quantity_allocated_map:
        item["warehouse_id"] = graphene.Node.to_global_id(
            "Warehouse", item["warehouse_id"]
        )
    return warehouse_id_quantity_allocated_map


@traced_payload_generator
def generate_order_lines_payload(lines: Iterable[OrderLine]):
    line_fields = (
        "product_name",
        "variant_name",
        "translated_product_name",
        "translated_variant_name",
        "product_sku",
        "quantity",
        "currency",
        "unit_price_net_amount",
        "unit_price_gross_amount",
        "unit_discount_amount",
        "unit_discount_type",
        "unit_discount_reason",
        "total_price_net_amount",
        "total_price_gross_amount",
        "undiscounted_unit_price_net_amount",
        "undiscounted_unit_price_gross_amount",
        "undiscounted_total_price_net_amount",
        "undiscounted_total_price_gross_amount",
        "tax_rate",
        "sale_id",
        "voucher_code",
    )
    line_price_fields = (
        "unit_price_gross_amount",
        "unit_price_net_amount",
        "unit_discount_amount",
        "total_price_net_amount",
        "total_price_gross_amount",
        "undiscounted_unit_price_net_amount",
        "undiscounted_unit_price_gross_amount",
        "undiscounted_total_price_net_amount",
        "undiscounted_total_price_gross_amount",
    )

    for line in lines:
        quantize_price_fields(line, line_price_fields, line.currency)

    serializer = PayloadSerializer()
    return serializer.serialize(
        lines,
        fields=line_fields,
        extra_dict_data={
            "product_variant_id": (lambda l: l.product_variant_id),
            "total_price_net_amount": (lambda l: l.total_price.net.amount),
            "total_price_gross_amount": (lambda l: l.total_price.gross.amount),
            "allocations": (lambda l: prepare_order_lines_allocations_payload(l)),
        },
    )


def _generate_collection_point_payload(warehouse: "Warehouse"):
    serializer = PayloadSerializer()
    collection_point_fields = (
        "name",
        "email",
        "click_and_collect_option",
        "is_private",
    )
    collection_point_data = serializer.serialize(
        [warehouse],
        fields=collection_point_fields,
        additional_fields={"address": (lambda w: w.address, ADDRESS_FIELDS)},
    )
    return collection_point_data


def _generate_shipping_method_payload(shipping_method, channel):
    if not shipping_method:
        return None

    serializer = PayloadSerializer()
    shipping_method_fields = ("name", "type")

    shipping_method_channel_listing = shipping_method.channel_listings.filter(
        channel=channel,
    ).first()

    payload = serializer.serialize(
        [shipping_method],
        fields=shipping_method_fields,
        extra_dict_data={
            "currency": shipping_method_channel_listing.currency,
            "price_amount": quantize_price(
                shipping_method_channel_listing.price_amount,
                shipping_method_channel_listing.currency,
            ),
        },
    )

    return json.loads(payload)[0]


@traced_payload_generator
def generate_order_payload(
    order: "Order",
    requestor: Optional["RequestorOrLazyObject"] = None,
    with_meta: bool = True,
):
    serializer = PayloadSerializer()
    fulfillment_fields = (
        "status",
        "tracking_number",
        "shipping_refund_amount",
        "total_refund_amount",
    )
    fulfillment_price_fields = ("shipping_refund_amount", "total_refund_amount")
    payment_price_fields = ("captured_amount", "total")
    discount_fields = (
        "type",
        "value_type",
        "value",
        "amount_value",
        "name",
        "translated_name",
        "reason",
    )
    discount_price_fields = ("amount_value",)

    lines = order.lines.all()
    fulfillments = order.fulfillments.all()
    payments = order.payments.all()
    discounts = order.discounts.all()

    quantize_price_fields(order, ORDER_PRICE_FIELDS, order.currency)

    for fulfillment in fulfillments:
        quantize_price_fields(fulfillment, fulfillment_price_fields, order.currency)

    for payment in payments:
        quantize_price_fields(payment, payment_price_fields, order.currency)

    for discount in discounts:
        quantize_price_fields(discount, discount_price_fields, order.currency)

    fulfillments_data = serializer.serialize(
        fulfillments,
        fields=fulfillment_fields,
        extra_dict_data={
            "lines": lambda f: json.loads(generate_fulfillment_lines_payload(f)),
            "created": lambda f: f.created_at,
        },
    )

    extra_dict_data = {
        "id": graphene.Node.to_global_id("Order", order.id),
        "token": str(order.id),
        "user_email": order.get_customer_email(),
        "created": order.created_at,
        "original": graphene.Node.to_global_id("Order", order.original_id),
        "lines": json.loads(generate_order_lines_payload(lines)),
        "fulfillments": json.loads(fulfillments_data),
        "collection_point": json.loads(
            _generate_collection_point_payload(order.collection_point)
        )[0]
        if order.collection_point
        else None,
        "payments": json.loads(_generate_order_payment_payload(payments)),
        "shipping_method": _generate_shipping_method_payload(
            order.shipping_method, order.channel
        ),
    }
    if with_meta:
        extra_dict_data["meta"] = generate_meta(
            requestor_data=generate_requestor(requestor)
        )

    order_data = serializer.serialize(
        [order],
        fields=ORDER_FIELDS,
        additional_fields={
            "channel": (lambda o: o.channel, CHANNEL_FIELDS),
            "shipping_address": (lambda o: o.shipping_address, ADDRESS_FIELDS),
            "billing_address": (lambda o: o.billing_address, ADDRESS_FIELDS),
            "discounts": (lambda _: discounts, discount_fields),
        },
        extra_dict_data=extra_dict_data,
    )
    return order_data


def _generate_order_payment_payload(payments: Iterable["Payment"]):
    payment_fields = (
        "gateway",
        "payment_method_type",
        "cc_brand",
        "is_active",
        "partial",
        "charge_status",
        "psp_reference",
        "total",
        "captured_amount",
        "currency",
        "billing_email",
        "billing_first_name",
        "billing_last_name",
        "billing_company_name",
        "billing_address_1",
        "billing_address_2",
        "billing_city",
        "billing_city_area",
        "billing_postal_code",
        "billing_country_code",
        "billing_country_area",
    )
    serializer = PayloadSerializer()
    return serializer.serialize(
        payments,
        fields=payment_fields,
        extra_dict_data={
            "created": lambda p: p.created_at,
            "modified": lambda p: p.modified_at,
        },
    )


def _calculate_added(
    previous_catalogue: DefaultDict[str, Set[str]],
    current_catalogue: DefaultDict[str, Set[str]],
    key: str,
) -> List[str]:
    return list(current_catalogue[key] - previous_catalogue[key])


def _calculate_removed(
    previous_catalogue: DefaultDict[str, Set[str]],
    current_catalogue: DefaultDict[str, Set[str]],
    key: str,
) -> List[str]:
    return _calculate_added(current_catalogue, previous_catalogue, key)


@traced_payload_generator
def generate_sale_payload(
    sale: "Sale",
    previous_catalogue: Optional[DefaultDict[str, Set[str]]] = None,
    current_catalogue: Optional[DefaultDict[str, Set[str]]] = None,
    requestor: Optional["RequestorOrLazyObject"] = None,
):
    if previous_catalogue is None:
        previous_catalogue = defaultdict(set)
    if current_catalogue is None:
        current_catalogue = defaultdict(set)

    serializer = PayloadSerializer()
    sale_fields = ("id",)

    return serializer.serialize(
        [sale],
        fields=sale_fields,
        extra_dict_data={
            "meta": generate_meta(requestor_data=generate_requestor(requestor)),
            "categories_added": _calculate_added(
                previous_catalogue, current_catalogue, "categories"
            ),
            "categories_removed": _calculate_removed(
                previous_catalogue, current_catalogue, "categories"
            ),
            "collections_added": _calculate_added(
                previous_catalogue, current_catalogue, "collections"
            ),
            "collections_removed": _calculate_removed(
                previous_catalogue, current_catalogue, "collections"
            ),
            "products_added": _calculate_added(
                previous_catalogue, current_catalogue, "products"
            ),
            "products_removed": _calculate_removed(
                previous_catalogue, current_catalogue, "products"
            ),
            "variants_added": _calculate_added(
                previous_catalogue, current_catalogue, "variants"
            ),
            "variants_removed": _calculate_removed(
                previous_catalogue, current_catalogue, "variants"
            ),
        },
    )


@traced_payload_generator
def generate_sale_toggle_payload(
    sale: "Sale",
    catalogue: DefaultDict[str, Set[str]],
    requestor: Optional["RequestorOrLazyObject"] = None,
):
    serializer = PayloadSerializer()
    sale_fields = ("id",)

    extra_dict_data = {key: list(ids) for key, ids in catalogue.items()}
    extra_dict_data["meta"] = generate_meta(
        requestor_data=generate_requestor(requestor)
    )
    extra_dict_data["is_active"] = sale.is_active()

    return serializer.serialize(
        [sale],
        fields=sale_fields,
        extra_dict_data=extra_dict_data,
    )


@traced_payload_generator
def generate_invoice_payload(
    invoice: "Invoice", requestor: Optional["RequestorOrLazyObject"] = None
):
    serializer = PayloadSerializer()
    invoice_fields = ("id", "number", "external_url", "created")
    if invoice.order is not None:
        quantize_price_fields(invoice.order, ORDER_PRICE_FIELDS, invoice.order.currency)
    return serializer.serialize(
        [invoice],
        fields=invoice_fields,
        extra_dict_data={
            "meta": generate_meta(requestor_data=generate_requestor(requestor)),
            "order": lambda i: json.loads(_generate_order_payload_for_invoice(i.order))[
                0
            ],
        },
    )


@traced_payload_generator
def _generate_order_payload_for_invoice(order: "Order"):
    # This is a temporary method that allows attaching an order token
    # that is no longer part of the order model.
    # The method should be removed after removing the deprecated order token field.
    # After that, we should move generating order data to the `additional_fields`
    # in the `generate_invoice_payload` method.
    serializer = PayloadSerializer()
    payload = serializer.serialize(
        [order],
        fields=ORDER_FIELDS,
        extra_dict_data={
            "token": order.id,
            "user_email": order.get_customer_email(),
            "created": order.created_at,
        },
    )
    return payload


@traced_payload_generator
def generate_checkout_payload(
    checkout: "Checkout", requestor: Optional["RequestorOrLazyObject"] = None
):
    serializer = PayloadSerializer()
    checkout_fields = (
        "last_change",
        "status",
        "email",
        "quantity",
        "currency",
        "discount_amount",
        "discount_name",
        "language_code",
        "private_metadata",
        "metadata",
    )

    checkout_price_fields = ("discount_amount",)
    quantize_price_fields(checkout, checkout_price_fields, checkout.currency)
    user_fields = ("email", "first_name", "last_name")

    discounts = fetch_active_discounts()
    lines_dict_data = serialize_checkout_lines(checkout, discounts)

    # todo use the most appropriate warehouse
    warehouse = None
    if checkout.shipping_address:
        warehouse = Warehouse.objects.for_country_and_channel(
            checkout.shipping_address.country.code, checkout.channel_id
        ).first()

    checkout_data = serializer.serialize(
        [checkout],
        fields=checkout_fields,
        pk_field_name="token",
        additional_fields={
            "channel": (lambda o: o.channel, CHANNEL_FIELDS),
            "user": (lambda c: c.user, user_fields),
            "billing_address": (lambda c: c.billing_address, ADDRESS_FIELDS),
            "shipping_address": (lambda c: c.shipping_address, ADDRESS_FIELDS),
            "warehouse_address": (
                lambda c: warehouse.address if warehouse else None,
                ADDRESS_FIELDS,
            ),
        },
        extra_dict_data={
            # Casting to list to make it json-serializable
            "shipping_method": _generate_shipping_method_payload(
                checkout.shipping_method, checkout.channel
            ),
            "lines": list(lines_dict_data),
            "collection_point": json.loads(
                _generate_collection_point_payload(checkout.collection_point)
            )[0]
            if checkout.collection_point
            else None,
            "meta": generate_meta(requestor_data=generate_requestor(requestor)),
            "created": checkout.created_at,
            # We add token as a graphql ID as it worked in that way since we introduce
            # a checkout payload
            "token": graphene.Node.to_global_id("Checkout", checkout.token),
        },
    )
    return checkout_data


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
            "default_shipping_address": (
                lambda c: c.default_shipping_address,
                ADDRESS_FIELDS,
            ),
            "default_billing_address": (
                lambda c: c.default_billing_address,
                ADDRESS_FIELDS,
            ),
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


def serialize_product_channel_listing_payload(channel_listings):
    serializer = PayloadSerializer()
    fields = (
        "published_at",
        "is_published",
        "visible_in_listings",
        "available_for_purchase_at",
    )
    channel_listing_payload = serializer.serialize(
        channel_listings,
        fields=fields,
        extra_dict_data={
            "channel_slug": lambda pch: pch.channel.slug,
            # deprecated in 3.3 - published_at and available_for_purchase_at
            # should be used instead
            "publication_date": lambda pch: pch.published_at,
            "available_for_purchase": lambda pch: pch.available_for_purchase_at,
        },
    )
    return channel_listing_payload



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


