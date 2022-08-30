from copy import copy
from dataclasses import dataclass
from decimal import Decimal
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.utils.functional import SimpleLazyObject
from django_countries.fields import Country
from graphene import Mutation
from graphql import GraphQLError, ResolveInfo
from graphql.execution import ExecutionResult
from prices import Money, TaxedMoney
from promise.promise import Promise

from ..core.models import EventDelivery

from .models import PluginConfiguration

if TYPE_CHECKING:
    # flake8: noqa
    from ..account.models import Address, Group, User
    from ..app.models import App
    from ..channel.models import Channel
    from ..core.middleware import Requestor
    from ..core.notify_events import NotifyEventType
    from ..menu.models import Menu, MenuItem
    from ..page.models import Page, PageType
    from ..post.models import Post, PostType

PluginConfigurationType = List[dict]
NoneType = type(None)
RequestorOrLazyObject = Union[SimpleLazyObject, "Requestor"]


class ConfigurationTypeField:
    STRING = "String"
    MULTILINE = "Multiline"
    BOOLEAN = "Boolean"
    SECRET = "Secret"
    SECRET_MULTILINE = "SecretMultiline"
    PASSWORD = "Password"
    OUTPUT = "OUTPUT"
    CHOICES = [
        (STRING, "Field is a String"),
        (MULTILINE, "Field is a Multiline"),
        (BOOLEAN, "Field is a Boolean"),
        (SECRET, "Field is a Secret"),
        (PASSWORD, "Field is a Password"),
        (SECRET_MULTILINE, "Field is a Secret multiline"),
        (OUTPUT, "Field is a read only"),
    ]


@dataclass
class ExternalAccessTokens:
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    csrf_token: Optional[str] = None
    user: Optional["User"] = None


@dataclass
class ExcludedShippingMethod:
    id: str
    reason: Optional[str]


class BasePlugin:
    """Abstract class for storing all methods available for any plugin.

    All methods take previous_value parameter.
    previous_value contains a value calculated by the previous plugin in the queue.
    If the plugin is first, it will use default value calculated by the manager.
    """

    PLUGIN_NAME = ""
    PLUGIN_ID = ""
    PLUGIN_DESCRIPTION = ""
    CONFIG_STRUCTURE = None
    CONFIGURATION_PER_CHANNEL = True
    DEFAULT_CONFIGURATION = []
    DEFAULT_ACTIVE = False
    HIDDEN = False

    @classmethod
    def check_plugin_id(cls, plugin_id: str) -> bool:
        """Check if given plugin_id matches with the PLUGIN_ID of this plugin."""
        return cls.PLUGIN_ID == plugin_id

    def __init__(
        self,
        *,
        configuration: PluginConfigurationType,
        active: bool,
        channel: Optional["Channel"] = None,
        requestor_getter: Optional[Callable[[], "Requestor"]] = None,
        db_config: Optional["PluginConfiguration"] = None
    ):
        self.configuration = self.get_plugin_configuration(configuration)
        self.active = active
        self.channel = channel
        self.requestor: Optional[RequestorOrLazyObject] = (
            SimpleLazyObject(requestor_getter) if requestor_getter else requestor_getter
        )
        self.db_config = db_config

    def __str__(self):
        return self.PLUGIN_NAME

    #  Trigger when address is created.
    #
    #  Overwrite this method if you need to trigger specific logic after an address is
    #  created.
    address_created: Callable[["Address", None], None]

    #  Trigger when address is deleted.
    #
    #  Overwrite this method if you need to trigger specific logic after an address is
    #  deleted.
    address_deleted: Callable[["Address", None], None]

    #  Trigger when address is updated.
    #
    #  Overwrite this method if you need to trigger specific logic after an address is
    #  updated.
    address_updated: Callable[["Address", None], None]

    #  Trigger when app is installed.
    #
    #  Overwrite this method if you need to trigger specific logic after an app is
    #  installed.
    app_installed: Callable[["App", None], None]

    #  Trigger when app is deleted.
    #
    #  Overwrite this method if you need to trigger specific logic after an app is
    #  deleted.
    app_deleted: Callable[["App", None], None]

    #  Trigger when app is updated.
    #
    #  Overwrite this method if you need to trigger specific logic after an app is
    #  updated.
    app_updated: Callable[["App", None], None]

    #  Trigger when channel status is changed.
    #
    #  Overwrite this method if you need to trigger specific logic after an app
    #  status is changed.
    app_status_changed: Callable[["App", None], None]

    #  Authenticate user which should be assigned to the request.
    #
    #  Overwrite this method if the plugin handles authentication flow.
    authenticate_user: Callable[
        [WSGIRequest, Optional["User"]], Union["User", NoneType]
    ]

    
    #  Trigger when channel is created.
    #
    #  Overwrite this method if you need to trigger specific logic after a channel is
    #  created.
    channel_created: Callable[["Channel", None], None]

    #  Trigger when channel is deleted.
    #
    #  Overwrite this method if you need to trigger specific logic after a channel is
    #  deleted.
    channel_deleted: Callable[["Channel", None], None]

    #  Trigger when channel is updated.
    #
    #  Overwrite this method if you need to trigger specific logic after a channel is
    #  updated.
    channel_updated: Callable[["Channel", None], None]

    #  Trigger when channel status is changed.
    #
    #  Overwrite this method if you need to trigger specific logic after a channel
    #  status is changed.
    channel_status_changed: Callable[["Channel", None], None]

    change_user_address: Callable[
        ["Address", Union[str, NoneType], Union["User", NoneType], "Address"], "Address"
    ]

    
    #  Trigger when user is created.
    #
    #  Overwrite this method if you need to trigger specific logic after a user is
    #  created.
    customer_created: Callable[["User", Any], Any]

    #  Trigger when user is deleted.
    #
    #  Overwrite this method if you need to trigger specific logic after a user is
    #  deleted.
    customer_deleted: Callable[["User", Any], Any]

    #  Trigger when user is updated.
    #
    #  Overwrite this method if you need to trigger specific logic after a user is
    #  updated.
    customer_updated: Callable[["User", Any], Any]

    #  Handle authentication request.
    #
    #  Overwrite this method if the plugin handles authentication flow.
    external_authentication_url: Callable[[dict, WSGIRequest, dict], dict]

    #  Handle logout request.
    #
    #  Overwrite this method if the plugin handles logout flow.
    external_logout: Callable[[dict, WSGIRequest, dict], Any]

    #  Handle authentication request responsible for obtaining access tokens.
    #
    #  Overwrite this method if the plugin handles authentication flow.
    external_obtain_access_tokens: Callable[
        [dict, WSGIRequest, ExternalAccessTokens], ExternalAccessTokens
    ]

    #  Handle authentication refresh request.
    #
    #  Overwrite this method if the plugin handles authentication flow and supports
    #  refreshing the access.
    external_refresh: Callable[
        [dict, WSGIRequest, ExternalAccessTokens], ExternalAccessTokens
    ]

    #  Verify the provided authentication data.
    #
    #  Overwrite this method if the plugin should validate the authentication data.
    external_verify: Callable[
        [dict, WSGIRequest, Tuple[Union["User", NoneType], dict]],
        Tuple[Union["User", NoneType], dict],
    ]

    get_client_token: Callable[[Any, Any], Any]

    #  Trigger when menu is created.
    #
    #  Overwrite this method if you need to trigger specific logic after a menu is
    #  created.
    menu_created: Callable[["Menu", None], None]

    #  Trigger when menu is deleted.
    #
    #  Overwrite this method if you need to trigger specific logic after a menu is
    #  deleted.
    menu_deleted: Callable[["Menu", None], None]

    #  Trigger when menu is updated.
    #
    #  Overwrite this method if you need to trigger specific logic after a menu is
    #  updated.
    menu_updated: Callable[["Menu", None], None]

    #  Trigger when menu item is created.
    #
    #  Overwrite this method if you need to trigger specific logic after a menu item is
    #  created.
    menu_item_created: Callable[["MenuItem", None], None]

    #  Trigger when menu item is deleted.
    #
    #  Overwrite this method if you need to trigger specific logic after a menu item is
    #  deleted.
    menu_item_deleted: Callable[["MenuItem", None], None]

    #  Trigger when menu item is updated.
    #
    #  Overwrite this method if you need to trigger specific logic after a menu item is
    #  updated.
    menu_item_updated: Callable[["MenuItem", None], None]

    #  Handle notification request.
    #
    #  Overwrite this method if the plugin is responsible for sending notifications.
    notify: Callable[["NotifyEventType", dict, Any], Any]

    #  Trigger when page is created.
    #
    #  Overwrite this method if you need to trigger specific logic when a page is
    #  created.
    page_created: Callable[["Page", Any], Any]

    #  Trigger when page is deleted.
    #
    #  Overwrite this method if you need to trigger specific logic when a page is
    #  deleted.
    page_deleted: Callable[["Page", Any], Any]

    #  Trigger when page is updated.
    #
    #  Overwrite this method if you need to trigger specific logic when a page is
    #  updated.
    page_updated: Callable[["Page", Any], Any]

    #  Trigger when page type is created.
    #
    #  Overwrite this method if you need to trigger specific logic when a page type is
    #  created.
    page_type_created: Callable[["PageType", Any], Any]

    #  Trigger when page type is deleted.
    #
    #  Overwrite this method if you need to trigger specific logic when a page type is
    #  deleted.
    page_type_deleted: Callable[["PageType", Any], Any]

    #  Trigger when page type is updated.
    #
    #  Overwrite this method if you need to trigger specific logic when a page type is
    #  updated.
    page_type_updated: Callable[["PageType", Any], Any]


    #  Trigger when post is created.
    #
    #  Overwrite this method if you need to trigger specific logic when a post is
    #  created.
    post_created: Callable[["Post", Any], Any]

    #  Trigger when post is deleted.
    #
    #  Overwrite this method if you need to trigger specific logic when a post is
    #  deleted.
    post_deleted: Callable[["Post", Any], Any]

    #  Trigger when post is updated.
    #
    #  Overwrite this method if you need to trigger specific logic when a post is
    #  updated.
    post_updated: Callable[["Post", Any], Any]

    #  Trigger when post type is created.
    #
    #  Overwrite this method if you need to trigger specific logic when a post type is
    #  created.
    post_type_created: Callable[["PostType", Any], Any]

    #  Trigger when post type is deleted.
    #
    #  Overwrite this method if you need to trigger specific logic when a post type is
    #  deleted.
    post_type_deleted: Callable[["PostType", Any], Any]

    #  Trigger when post type is updated.
    #
    #  Overwrite this method if you need to trigger specific logic when a post type is
    #  updated.
    post_type_updated: Callable[["PostType", Any], Any]

    #  Trigger when permission group is created.
    #
    #  Overwrite this method if you need to trigger specific logic when a permission
    #  group is created.
    permission_group_created: Callable[["Group", Any], Any]

    #  Trigger when permission group type is deleted.
    #
    #  Overwrite this method if you need to trigger specific logic when a permission
    #  group is deleted.
    permission_group_deleted: Callable[["Group", Any], Any]

    #  Trigger when permission group is updated.
    #
    #  Overwrite this method if you need to trigger specific logic when a permission
    #  group is updated.
    permission_group_updated: Callable[["Group", Any], Any]

    #  Trigger when staff user is created.
    #
    #  Overwrite this method if you need to trigger specific logic after a staff user is
    #  created.
    staff_created: Callable[["User", Any], Any]

    #  Trigger when staff user is updated.
    #
    #  Overwrite this method if you need to trigger specific logic after a staff user is
    #  updated.
    staff_updated: Callable[["User", Any], Any]

    #  Trigger when staff user is deleted.
    #
    #  Overwrite this method if you need to trigger specific logic after a staff user is
    #  deleted.
    staff_deleted: Callable[["User", Any], Any]

    #  Handle received http request.
    #
    #  Overwrite this method if the plugin expects the incoming requests.
    webhook: Callable[[WSGIRequest, str, Any], HttpResponse]

    # Triggers retry mechanism for event delivery
    event_delivery_retry: Callable[["EventDelivery", Any], EventDelivery]

    # Invoked before each mutation is executed
    #
    # This allows to trigger specific logic before the mutation is executed
    # but only once the permissions are checked.
    #
    # Returns one of:
    #     - null if the execution shall continue
    #     - an execution result
    #     - graphql.GraphQLError
    perform_mutation: Callable[
        [
            Optional[Union[ExecutionResult, GraphQLError]],  # previous value
            Mutation,  # mutation class
            Any,  # mutation root
            ResolveInfo,  # resolve info
            dict,  # mutation data
        ],
        Optional[Union[ExecutionResult, GraphQLError]],
    ]

    def token_is_required_as_payment_input(self, previous_value):
        return previous_value


    @classmethod
    def _update_config_items(
        cls, configuration_to_update: List[dict], current_config: List[dict]
    ):
        config_structure: dict = (
            cls.CONFIG_STRUCTURE if cls.CONFIG_STRUCTURE is not None else {}
        )
        for config_item in current_config:
            for config_item_to_update in configuration_to_update:
                config_item_name = config_item_to_update.get("name")
                if config_item["name"] == config_item_name:
                    new_value = config_item_to_update.get("value")
                    item_type = config_structure.get(config_item_name, {}).get("type")
                    if (
                        item_type == ConfigurationTypeField.BOOLEAN
                        and new_value
                        and not isinstance(new_value, bool)
                    ):
                        new_value = new_value.lower() == "true"
                    if item_type == ConfigurationTypeField.OUTPUT:
                        # OUTPUT field is read only. No need to update it
                        continue
                    config_item.update([("value", new_value)])

        # Get new keys that don't exist in current_config and extend it.
        current_config_keys = set(c_field["name"] for c_field in current_config)
        configuration_to_update_dict = {
            c_field["name"]: c_field["value"] for c_field in configuration_to_update
        }
        missing_keys = set(configuration_to_update_dict.keys()) - current_config_keys
        for missing_key in missing_keys:
            if not config_structure.get(missing_key):
                continue
            current_config.append(
                {
                    "name": missing_key,
                    "value": configuration_to_update_dict[missing_key],
                }
            )

    @classmethod
    def validate_plugin_configuration(
        cls, plugin_configuration: "PluginConfiguration", **kwargs
    ):
        """Validate if provided configuration is correct.

        Raise django.core.exceptions.ValidationError otherwise.
        """
        return

    @classmethod
    def pre_save_plugin_configuration(cls, plugin_configuration: "PluginConfiguration"):
        """Trigger before plugin configuration will be saved.

        Overwrite this method if you need to trigger specific logic before saving a
        plugin configuration.
        """

    @classmethod
    def save_plugin_configuration(
        cls, plugin_configuration: "PluginConfiguration", cleaned_data
    ):
        current_config = plugin_configuration.configuration
        configuration_to_update = cleaned_data.get("configuration")
        if configuration_to_update:
            cls._update_config_items(configuration_to_update, current_config)

        if "active" in cleaned_data:
            plugin_configuration.active = cleaned_data["active"]

        cls.validate_plugin_configuration(plugin_configuration)
        cls.pre_save_plugin_configuration(plugin_configuration)
        plugin_configuration.save()

        if plugin_configuration.configuration:
            # Let's add a translated descriptions and labels
            cls._append_config_structure(plugin_configuration.configuration)
        return plugin_configuration

    @classmethod
    def _append_config_structure(cls, configuration: PluginConfigurationType):
        """Append configuration structure to config from the database.

        Database stores "key: value" pairs, the definition of fields should be declared
        inside of the plugin. Based on this, the plugin will generate a structure of
        configuration with current values and provide access to it via API.
        """
        config_structure = getattr(cls, "CONFIG_STRUCTURE") or {}
        fields_without_structure = []
        for configuration_field in configuration:

            structure_to_add = config_structure.get(configuration_field.get("name"))
            if structure_to_add:
                configuration_field.update(structure_to_add)
            else:
                fields_without_structure.append(configuration_field)

        if fields_without_structure:
            [
                configuration.remove(field)  # type: ignore
                for field in fields_without_structure
            ]

    @classmethod
    def _update_configuration_structure(cls, configuration: PluginConfigurationType):
        updated_configuration = []
        config_structure = getattr(cls, "CONFIG_STRUCTURE") or {}
        desired_config_keys = set(config_structure.keys())
        for config_field in configuration:
            if config_field["name"] not in desired_config_keys:
                continue
            updated_configuration.append(copy(config_field))

        configured_keys = set(d["name"] for d in updated_configuration)
        missing_keys = desired_config_keys - configured_keys

        if not missing_keys:
            return updated_configuration

        default_config = cls.DEFAULT_CONFIGURATION
        if not default_config:
            return updated_configuration

        update_values = [copy(k) for k in default_config if k["name"] in missing_keys]
        if update_values:
            updated_configuration.extend(update_values)
        return updated_configuration

    @classmethod
    def get_default_active(cls):
        return cls.DEFAULT_ACTIVE

    def get_plugin_configuration(
        self, configuration: PluginConfigurationType
    ) -> PluginConfigurationType:
        if not configuration:
            configuration = []
        configuration = self._update_configuration_structure(configuration)
        if configuration:
            # Let's add a translated descriptions and labels
            self._append_config_structure(configuration)
        return configuration

    def resolve_plugin_configuration(
        self, request
    ) -> Union[PluginConfigurationType, Promise[PluginConfigurationType]]:
        # Override this function to customize resolving plugin configuration in API.
        return self.configuration

    def is_event_active(self, event: str, channel=Optional[str]):
        return hasattr(self, event)
