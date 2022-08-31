import datetime
from typing import DefaultDict, Dict, Iterable, List

import graphene
import pytz
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from ...channel import models
from ...core.permissions import ChannelPermissions
from ...core.tracing import traced_atomic_transaction
from ...core.utils.date_time import convert_to_utc_date_time
from ..core.descriptions import ADDED_IN_31, ADDED_IN_35, PREVIEW_FEATURE
from ..core.mutations import BaseMutation, ModelDeleteMutation, ModelMutation
from ..core.types import ChannelError, ChannelErrorCode, NonNullList
from ..core.utils import get_duplicated_values, get_duplicates_items
from ..utils.validators import check_for_duplicates
from .types import Channel


class ChannelInput(graphene.InputObjectType):
    is_active = graphene.Boolean(description="isActive flag.")


class ChannelCreateInput(ChannelInput):
    name = graphene.String(description="Name of the channel.", required=True)
    slug = graphene.String(description="Slug of the channel.", required=True)


class ChannelCreate(ModelMutation):
    class Arguments:
        input = ChannelCreateInput(
            required=True, description="Fields required to create channel."
        )

    class Meta:
        description = "Creates new channel."
        model = models.Channel
        object_type = Channel
        permissions = (ChannelPermissions.MANAGE_CHANNELS,)
        error_type_class = ChannelError
        error_type_field = "channel_errors"

    @classmethod
    def get_type_for_model(cls):
        return Channel

    @classmethod
    def clean_input(cls, info, instance, data, input_cls=None):
        cleaned_input = super().clean_input(info, instance, data)
        slug = cleaned_input.get("slug")
        if slug:
            cleaned_input["slug"] = slugify(slug)

        return cleaned_input

    @classmethod
    @traced_atomic_transaction()
    def _save_m2m(cls, info, instance, cleaned_data):
        super()._save_m2m(info, instance, cleaned_data)


    @classmethod
    def post_save_action(cls, info, instance, cleaned_input):
        info.context.plugins.channel_created(instance)


class ChannelUpdateInput(ChannelInput):
    name = graphene.String(description="Name of the channel.")
    slug = graphene.String(description="Slug of the channel.")


class ChannelUpdate(ModelMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a channel to update.")
        input = ChannelUpdateInput(
            description="Fields required to update a channel.", required=True
        )

    class Meta:
        description = "Update a channel."
        model = models.Channel
        object_type = Channel
        permissions = (ChannelPermissions.MANAGE_CHANNELS,)
        error_type_class = ChannelError
        error_type_field = "channel_errors"

    @classmethod
    def clean_input(cls, info, instance, data, input_cls=None):
        errors = {}
        if error := check_for_duplicates(
            data, "add_shipping_zones", "remove_shipping_zones", "shipping_zones"
        ):
            error.code = ChannelErrorCode.DUPLICATED_INPUT_ITEM.value
            errors["shipping_zones"] = error

        if error := check_for_duplicates(
            data, "add_warehouses", "remove_warehouses", "warehouses"
        ):
            error.code = ChannelErrorCode.DUPLICATED_INPUT_ITEM.value
            errors["warehouses"] = error

        if errors:
            raise ValidationError(errors)

        cleaned_input = super().clean_input(info, instance, data)
        slug = cleaned_input.get("slug")
        if slug:
            cleaned_input["slug"] = slugify(slug)

        return cleaned_input


    @classmethod
    def post_save_action(cls, info, instance, cleaned_input):
        info.context.plugins.channel_updated(instance)


class ChannelDeleteInput(graphene.InputObjectType):
    channel_id = graphene.ID(
        required=True,
        description="ID of channel to migrate orders from origin channel.",
    )


class ChannelDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a channel to delete.")
        input = ChannelDeleteInput(description="Fields required to delete a channel.")

    class Meta:
        description = (
            "Delete a channel. Orders associated with the deleted "
            "channel will be moved to the target channel. "
            "Checkouts, product availability, and pricing will be removed."
        )
        model = models.Channel
        object_type = Channel
        permissions = (ChannelPermissions.MANAGE_CHANNELS,)
        error_type_class = ChannelError
        error_type_field = "channel_errors"

    @classmethod
    def validate_input(cls, origin_channel, target_channel):
        if origin_channel.id == target_channel.id:
            raise ValidationError(
                {
                    "channel_id": ValidationError(
                        "Cannot migrate data to the channel that is being removed.",
                        code=ChannelErrorCode.INVALID,
                    )
                }
            )
        origin_channel_currency = origin_channel.currency_code
        target_channel_currency = target_channel.currency_code
        if origin_channel_currency != target_channel_currency:
            raise ValidationError(
                {
                    "channel_id": ValidationError(
                        f"Cannot migrate from {origin_channel_currency} "
                        f"to {target_channel_currency}. "
                        "Migration are allowed between the same currency",
                        code=ChannelErrorCode.CHANNELS_CURRENCY_MUST_BE_THE_SAME,
                    )
                }
            )



    @classmethod
    def post_save_action(cls, info, instance, cleaned_input):
        info.context.plugins.channel_deleted(instance)


ErrorType = DefaultDict[str, List[ValidationError]]


class BaseChannelListingMutation(BaseMutation):
    """Base channel listing mutation with basic channel validation."""

    class Meta:
        abstract = True

    @classmethod
    def validate_duplicated_channel_ids(
        cls,
        add_channels_ids: Iterable[str],
        remove_channels_ids: Iterable[str],
        errors: ErrorType,
        error_code,
    ):
        duplicated_ids = get_duplicates_items(add_channels_ids, remove_channels_ids)
        if duplicated_ids:
            error_msg = (
                "The same object cannot be in both lists "
                "for adding and removing items."
            )
            errors["input"].append(
                ValidationError(
                    error_msg,
                    code=error_code,
                    params={"channels": list(duplicated_ids)},
                )
            )

    @classmethod
    def validate_duplicated_channel_values(
        cls, channels_ids: Iterable[str], field_name: str, errors: ErrorType, error_code
    ):
        duplicates = get_duplicated_values(channels_ids)
        if duplicates:
            errors[field_name].append(
                ValidationError(
                    "Duplicated channel ID.",
                    code=error_code,
                    params={"channels": duplicates},
                )
            )

    @classmethod
    def clean_channels(
        cls, info, input, errors: ErrorType, error_code, input_source="add_channels"
    ) -> Dict:
        add_channels = input.get(input_source, [])
        add_channels_ids = [channel["channel_id"] for channel in add_channels]
        remove_channels_ids = input.get("remove_channels", [])
        cls.validate_duplicated_channel_ids(
            add_channels_ids, remove_channels_ids, errors, error_code
        )
        cls.validate_duplicated_channel_values(
            add_channels_ids, input_source, errors, error_code
        )
        cls.validate_duplicated_channel_values(
            remove_channels_ids, "remove_channels", errors, error_code
        )

        if errors:
            return {}
        channels_to_add: List["models.Channel"] = []
        if add_channels_ids:
            channels_to_add = cls.get_nodes_or_error(  # type: ignore
                add_channels_ids, "channel_id", Channel
            )
        remove_channels_pks = cls.get_global_ids_or_error(
            remove_channels_ids, Channel, field="remove_channels"
        )

        cleaned_input = {input_source: [], "remove_channels": remove_channels_pks}

        for channel_listing, channel in zip(add_channels, channels_to_add):
            channel_listing["channel"] = channel
            cleaned_input[input_source].append(channel_listing)

        return cleaned_input

    @classmethod
    def clean_publication_date(
        cls, errors, error_code_enum, cleaned_input, input_source="add_channels"
    ):
        invalid_channels = []
        for add_channel in cleaned_input.get(input_source, []):
            # should update errors dict
            if "publication_date" in add_channel and "published_at" in add_channel:
                invalid_channels.append(add_channel["channel_id"])
                continue
            publication_date = add_channel.get("publication_date")
            publication_date = (
                convert_to_utc_date_time(publication_date)
                if publication_date
                else add_channel.get("published_at")
            )
            is_published = add_channel.get("is_published")
            if is_published and not publication_date:
                add_channel["published_at"] = datetime.datetime.now(pytz.UTC)
            elif "publication_date" in add_channel or "published_at" in add_channel:
                add_channel["published_at"] = publication_date
        if invalid_channels:
            error_msg = (
                "Only one of argument: publicationDate or publishedAt "
                "must be specified."
            )
            errors["publication_date"].append(
                ValidationError(
                    error_msg,
                    code=error_code_enum.INVALID.value,
                    params={"channels": invalid_channels},
                )
            )


class ChannelActivate(BaseMutation):
    channel = graphene.Field(Channel, description="Activated channel.")

    class Arguments:
        id = graphene.ID(required=True, description="ID of the channel to activate.")

    class Meta:
        description = "Activate a channel."
        permissions = (ChannelPermissions.MANAGE_CHANNELS,)
        error_type_class = ChannelError
        error_type_field = "channel_errors"

    @classmethod
    def clean_channel_availability(cls, channel):
        if channel.is_active:
            raise ValidationError(
                {
                    "id": ValidationError(
                        "This channel is already activated.",
                        code=ChannelErrorCode.INVALID,
                    )
                }
            )

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        channel = cls.get_node_or_error(info, data["id"], only_type=Channel)
        cls.clean_channel_availability(channel)
        channel.is_active = True
        channel.save(update_fields=["is_active"])
        info.context.plugins.channel_status_changed(channel)
        return ChannelActivate(channel=channel)


class ChannelDeactivate(BaseMutation):
    channel = graphene.Field(Channel, description="Deactivated channel.")

    class Arguments:
        id = graphene.ID(required=True, description="ID of the channel to deactivate.")

    class Meta:
        description = "Deactivate a channel."
        permissions = (ChannelPermissions.MANAGE_CHANNELS,)
        error_type_class = ChannelError
        error_type_field = "channel_errors"

    @classmethod
    def clean_channel_availability(cls, channel):
        if channel.is_active is False:
            raise ValidationError(
                {
                    "id": ValidationError(
                        "This channel is already deactivated.",
                        code=ChannelErrorCode.INVALID,
                    )
                }
            )

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        channel = cls.get_node_or_error(info, data["id"], only_type=Channel)
        cls.clean_channel_availability(channel)
        channel.is_active = False
        channel.save(update_fields=["is_active"])
        info.context.plugins.channel_status_changed(channel)
        return ChannelDeactivate(channel=channel)
