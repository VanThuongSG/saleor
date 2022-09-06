from collections import defaultdict
from decimal import Decimal
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

import opentracing
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, HttpResponseNotFound
from django.utils.module_loading import import_string
from graphene import Mutation
from graphql import GraphQLError, ResolveInfo
from graphql.execution import ExecutionResult
from abc import ABC

from ..channel.models import Channel
from ..core.models import EventDelivery
from .base_plugin import ExternalAccessTokens
from .models import PluginConfiguration

if TYPE_CHECKING:
    # flake8: noqa
    from ..account.models import Address, Group, User
    from ..app.models import App
    from ..core.middleware import Requestor
    from ..menu.models import Menu, MenuItem
    from ..page.models import Page, PageType
    from ..post.models import Category, Post, PostType
    from .base_plugin import BasePlugin

NotifyEventTypeChoice = str


# class PluginsManager(PaymentInterface):
class PluginsManager(ABC):
    """Base manager for handling plugins logic."""

    plugins_per_channel: Dict[str, List["BasePlugin"]] = {}
    global_plugins: List["BasePlugin"] = []
    all_plugins: List["BasePlugin"] = []

    def _load_plugin(
        self,
        PluginClass: Type["BasePlugin"],
        db_configs_map: dict,
        channel: Optional["Channel"] = None,
        requestor_getter=None,
    ) -> "BasePlugin":
        db_config = None
        if PluginClass.PLUGIN_ID in db_configs_map:
            db_config = db_configs_map[PluginClass.PLUGIN_ID]
            plugin_config = db_config.configuration
            active = db_config.active
            channel = db_config.channel
        else:
            plugin_config = PluginClass.DEFAULT_CONFIGURATION
            active = PluginClass.get_default_active()

        return PluginClass(
            configuration=plugin_config,
            active=active,
            channel=channel,
            requestor_getter=requestor_getter,
            db_config=db_config,
        )

    def __init__(self, plugins: List[str], requestor_getter=None):
        with opentracing.global_tracer().start_active_span("PluginsManager.__init__"):
            self.all_plugins = []
            self.global_plugins = []
            self.plugins_per_channel = defaultdict(list)

            global_db_configs, channel_db_configs = self._get_db_plugin_configs()
            channels = Channel.objects.all()

            for plugin_path in plugins:
                with opentracing.global_tracer().start_active_span(f"{plugin_path}"):
                    PluginClass = import_string(plugin_path)
                    if not getattr(PluginClass, "CONFIGURATION_PER_CHANNEL", False):
                        plugin = self._load_plugin(
                            PluginClass,
                            global_db_configs,
                            requestor_getter=requestor_getter,
                        )
                        self.global_plugins.append(plugin)
                        self.all_plugins.append(plugin)
                    else:
                        for channel in channels:
                            channel_configs = channel_db_configs.get(channel, {})
                            plugin = self._load_plugin(
                                PluginClass, channel_configs, channel, requestor_getter
                            )
                            self.plugins_per_channel[channel.slug].append(plugin)
                            self.all_plugins.append(plugin)

            for channel in channels:
                self.plugins_per_channel[channel.slug].extend(self.global_plugins)

    def _get_db_plugin_configs(self):
        with opentracing.global_tracer().start_active_span("_get_db_plugin_configs"):
            qs = (
                PluginConfiguration.objects.all()
                .using(settings.DATABASE_CONNECTION_REPLICA_NAME)
                .prefetch_related("channel")
            )
            channel_configs = defaultdict(dict)
            global_configs = {}
            for db_plugin_config in qs:
                channel = db_plugin_config.channel
                if channel is None:
                    global_configs[db_plugin_config.identifier] = db_plugin_config
                else:
                    channel_configs[channel][
                        db_plugin_config.identifier
                    ] = db_plugin_config
            return global_configs, channel_configs

    def __run_method_on_plugins(
        self,
        method_name: str,
        default_value: Any,
        *args,
        channel_slug: Optional[str] = None,
        **kwargs
    ):
        """Try to run a method with the given name on each declared active plugin."""
        value = default_value
        plugins = self.get_plugins(channel_slug=channel_slug, active_only=True)
        for plugin in plugins:
            value = self.__run_method_on_single_plugin(
                plugin, method_name, value, *args, **kwargs
            )
        return value

    def __run_method_on_single_plugin(
        self,
        plugin: Optional["BasePlugin"],
        method_name: str,
        previous_value: Any,
        *args,
        **kwargs,
    ) -> Any:
        """Run method_name on plugin.

        Method will return value returned from plugin's
        method. If plugin doesn't have own implementation of expected method_name, it
        will return previous_value.
        """
        plugin_method = getattr(plugin, method_name, NotImplemented)
        if plugin_method == NotImplemented:
            return previous_value
        returned_value = plugin_method(
            *args, **kwargs, previous_value=previous_value
        )  # type:ignore
        if returned_value == NotImplemented:
            return previous_value
        return returned_value

    def check_payment_balance(self, details: dict, channel_slug: str) -> dict:
        return self.__run_method_on_plugins(
            "check_payment_balance", None, details, channel_slug=channel_slug
        )

    def change_user_address(
        self, address: "Address", user: Optional["User"]
    ) -> "Address":
        default_value = address
        return self.__run_method_on_plugins(
            "change_user_address", default_value, address, user
        )

    def customer_created(self, customer: "User"):
        default_value = None
        return self.__run_method_on_plugins("customer_created", default_value, customer)

    def customer_deleted(self, customer: "User"):
        default_value = None
        return self.__run_method_on_plugins("customer_deleted", default_value, customer)

    def customer_updated(self, customer: "User"):
        default_value = None
        return self.__run_method_on_plugins("customer_updated", default_value, customer)

    
    def event_delivery_retry(self, event_delivery: "EventDelivery"):
        default_value = None
        return self.__run_method_on_plugins(
            "event_delivery_retry", default_value, event_delivery
        )
    
    def page_created(self, page: "Page"):
        default_value = None
        return self.__run_method_on_plugins("page_created", default_value, page)

    def page_updated(self, page: "Page"):
        default_value = None
        return self.__run_method_on_plugins("page_updated", default_value, page)

    def page_deleted(self, page: "Page"):
        default_value = None
        return self.__run_method_on_plugins("page_deleted", default_value, page)

    def page_type_created(self, page_type: "PageType"):
        default_value = None
        return self.__run_method_on_plugins(
            "page_type_created", default_value, page_type
        )

    def page_type_updated(self, page_type: "PageType"):
        default_value = None
        return self.__run_method_on_plugins(
            "page_type_updated", default_value, page_type
        )

    def page_type_deleted(self, page_type: "PageType"):
        default_value = None
        return self.__run_method_on_plugins(
            "page_type_deleted", default_value, page_type
        )

    def post_created(self, post: "Post"):
        default_value = None
        return self.__run_method_on_plugins("post_created", default_value, post)

    def post_updated(self, post: "Post"):
        default_value = None
        return self.__run_method_on_plugins("post_updated", default_value, post)

    def postdeleted(self, post: "Post"):
        default_value = None
        return self.__run_method_on_plugins("post_deleted", default_value, post)

    def post_type_created(self, post_type: "PostType"):
        default_value = None
        return self.__run_method_on_plugins(
            "post_type_created", default_value, post_type
        )

    def post_type_updated(self, post_type: "PostType"):
        default_value = None
        return self.__run_method_on_plugins(
            "post_type_updated", default_value, post_type
        )

    def post_type_deleted(self, post_type: "PostType"):
        default_value = None
        return self.__run_method_on_plugins(
            "post_type_deleted", default_value, post_type
        )

    def permission_group_created(self, group: "Group"):
        default_value = None
        return self.__run_method_on_plugins(
            "permission_group_created", default_value, group
        )

    def permission_group_updated(self, group: "Group"):
        default_value = None
        return self.__run_method_on_plugins(
            "permission_group_updated", default_value, group
        )

    def permission_group_deleted(self, group: "Group"):
        default_value = None
        return self.__run_method_on_plugins(
            "permission_group_deleted", default_value, group
        )

    def address_created(self, address: "Address"):
        default_value = None
        return self.__run_method_on_plugins("address_created", default_value, address)

    def address_updated(self, address: "Address"):
        default_value = None
        return self.__run_method_on_plugins("address_updated", default_value, address)

    def address_deleted(self, address: "Address"):
        default_value = None
        return self.__run_method_on_plugins("address_deleted", default_value, address)

    def app_installed(self, app: "App"):
        default_value = None
        return self.__run_method_on_plugins("app_installed", default_value, app)

    def app_updated(self, app: "App"):
        default_value = None
        return self.__run_method_on_plugins("app_updated", default_value, app)

    def app_deleted(self, app: "App"):
        default_value = None
        return self.__run_method_on_plugins("app_deleted", default_value, app)

    def app_status_changed(self, app: "App"):
        default_value = None
        return self.__run_method_on_plugins("app_status_changed", default_value, app)

    def category_created(self, category: "Category"):
        default_value = None
        return self.__run_method_on_plugins("category_created", default_value, category)

    def category_updated(self, category: "Category"):
        default_value = None
        return self.__run_method_on_plugins("category_updated", default_value, category)

    def category_deleted(self, category: "Category"):
        default_value = None
        return self.__run_method_on_plugins("category_deleted", default_value, category)

    def channel_created(self, channel: "Channel"):
        default_value = None
        return self.__run_method_on_plugins("channel_created", default_value, channel)

    def channel_updated(self, channel: "Channel"):
        default_value = None
        return self.__run_method_on_plugins("channel_updated", default_value, channel)

    def channel_deleted(self, channel: "Channel"):
        default_value = None
        return self.__run_method_on_plugins("channel_deleted", default_value, channel)

    def channel_status_changed(self, channel: "Channel"):
        default_value = None
        return self.__run_method_on_plugins(
            "channel_status_changed", default_value, channel
        )
    
    def menu_created(self, menu: "Menu"):
        default_value = None
        return self.__run_method_on_plugins("menu_created", default_value, menu)

    def menu_updated(self, menu: "Menu"):
        default_value = None
        return self.__run_method_on_plugins("menu_updated", default_value, menu)

    def menu_deleted(self, menu: "Menu"):
        default_value = None
        return self.__run_method_on_plugins("menu_deleted", default_value, menu)

    def menu_item_created(self, menu_item: "MenuItem"):
        default_value = None
        return self.__run_method_on_plugins(
            "menu_item_created", default_value, menu_item
        )

    def menu_item_updated(self, menu_item: "MenuItem"):
        default_value = None
        return self.__run_method_on_plugins(
            "menu_item_updated", default_value, menu_item
        )

    def menu_item_deleted(self, menu_item: "MenuItem"):
        default_value = None
        return self.__run_method_on_plugins(
            "menu_item_deleted", default_value, menu_item
        )
    
    def staff_created(self, staff_user: "User"):
        default_value = None
        return self.__run_method_on_plugins("staff_created", default_value, staff_user)

    def staff_updated(self, staff_user: "User"):
        default_value = None
        return self.__run_method_on_plugins("staff_updated", default_value, staff_user)

    def staff_deleted(self, staff_user: "User"):
        default_value = None
        return self.__run_method_on_plugins("staff_deleted", default_value, staff_user)

   
    def get_plugins(
        self, channel_slug: Optional[str] = None, active_only=False
    ) -> List["BasePlugin"]:
        """Return list of plugins for a given channel."""
        if channel_slug:
            plugins = self.plugins_per_channel[channel_slug]
        else:
            plugins = self.all_plugins

        if active_only:
            plugins = [plugin for plugin in plugins if plugin.active]
        return plugins

    
    def list_external_authentications(self, active_only: bool = True) -> List[dict]:
        auth_basic_method = "external_obtain_access_tokens"
        plugins = self.get_plugins(active_only=active_only)
        return [
            {"id": plugin.PLUGIN_ID, "name": plugin.PLUGIN_NAME}
            for plugin in plugins
            if auth_basic_method in type(plugin).__dict__
        ]

    
    def _get_all_plugin_configs(self):
        with opentracing.global_tracer().start_active_span("_get_all_plugin_configs"):
            if not hasattr(self, "_plugin_configs"):
                plugin_configurations = PluginConfiguration.objects.prefetch_related(
                    "channel"
                ).all()
                self._plugin_configs_per_channel = defaultdict(dict)
                self._global_plugin_configs = {}
                for pc in plugin_configurations:
                    channel = pc.channel
                    if channel is None:
                        self._global_plugin_configs[pc.identifier] = pc
                    else:
                        self._plugin_configs_per_channel[channel][pc.identifier] = pc
            return self._global_plugin_configs, self._plugin_configs_per_channel

    def save_plugin_configuration(
        self, plugin_id, channel_slug: Optional[str], cleaned_data: dict
    ):
        if channel_slug:
            plugins = self.get_plugins(channel_slug=channel_slug)
            channel = Channel.objects.filter(slug=channel_slug).first()
            if not channel:
                return None
        else:
            channel = None
            plugins = self.global_plugins

        for plugin in plugins:
            if plugin.PLUGIN_ID == plugin_id:
                plugin_configuration, _ = PluginConfiguration.objects.get_or_create(
                    identifier=plugin_id,
                    channel=channel,
                    defaults={"configuration": plugin.configuration},
                )
                configuration = plugin.save_plugin_configuration(
                    plugin_configuration, cleaned_data
                )
                configuration.name = plugin.PLUGIN_NAME
                configuration.description = plugin.PLUGIN_DESCRIPTION
                plugin.active = configuration.active
                plugin.configuration = configuration.configuration
                return configuration

    def get_plugin(
        self, plugin_id: str, channel_slug: Optional[str] = None
    ) -> Optional["BasePlugin"]:
        plugins = self.get_plugins(channel_slug=channel_slug)
        for plugin in plugins:
            if plugin.check_plugin_id(plugin_id):
                return plugin
        return None

    def webhook_endpoint_without_channel(
        self, request: WSGIRequest, plugin_id: str
    ) -> HttpResponse:
        # This should be removed in 3.0.0-a.25 as we want to give a possibility to have
        # no downtime between RCs
        split_path = request.path.split(plugin_id, maxsplit=1)
        path = None
        if len(split_path) == 2:
            path = split_path[1]

        default_value = HttpResponseNotFound()
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            return default_value
        return self.__run_method_on_single_plugin(
            plugin, "webhook", default_value, request, path
        )

    def webhook(
        self, request: WSGIRequest, plugin_id: str, channel_slug: Optional[str] = None
    ) -> HttpResponse:
        split_path = request.path.split(plugin_id, maxsplit=1)
        path = None
        if len(split_path) == 2:
            path = split_path[1]

        default_value = HttpResponseNotFound()
        plugin = self.get_plugin(plugin_id, channel_slug=channel_slug)
        if not plugin:
            return default_value

        if not plugin.active:
            return default_value

        if plugin.CONFIGURATION_PER_CHANNEL and not channel_slug:
            return HttpResponseNotFound(
                "Incorrect endpoint. Use /plugins/channel/<channel_slug>/"
                f"{plugin.PLUGIN_ID}/"
            )

        return self.__run_method_on_single_plugin(
            plugin, "webhook", default_value, request, path
        )

    def notify(
        self,
        event: "NotifyEventTypeChoice",
        payload: dict,
        channel_slug: Optional[str] = None,
        plugin_id: Optional[str] = None,
    ):
        default_value = None
        if plugin_id:
            plugin = self.get_plugin(plugin_id, channel_slug=channel_slug)
            return self.__run_method_on_single_plugin(
                plugin=plugin,
                method_name="notify",
                previous_value=default_value,
                event=event,
                payload=payload,
            )
        return self.__run_method_on_plugins(
            "notify", default_value, event, payload, channel_slug=channel_slug
        )

    def external_obtain_access_tokens(
        self, plugin_id: str, data: dict, request: WSGIRequest
    ) -> Optional["ExternalAccessTokens"]:
        """Obtain access tokens from authentication plugin."""
        default_value = ExternalAccessTokens()
        plugin = self.get_plugin(plugin_id)
        return self.__run_method_on_single_plugin(
            plugin, "external_obtain_access_tokens", default_value, data, request
        )

    def external_authentication_url(
        self, plugin_id: str, data: dict, request: WSGIRequest
    ) -> dict:
        """Handle authentication request."""
        default_value = {}  # type: ignore
        plugin = self.get_plugin(plugin_id)
        return self.__run_method_on_single_plugin(
            plugin, "external_authentication_url", default_value, data, request
        )

    def external_refresh(
        self, plugin_id: str, data: dict, request: WSGIRequest
    ) -> Optional["ExternalAccessTokens"]:
        """Handle authentication refresh request."""
        default_value = ExternalAccessTokens()
        plugin = self.get_plugin(plugin_id)
        return self.__run_method_on_single_plugin(
            plugin, "external_refresh", default_value, data, request
        )

    def authenticate_user(self, request: WSGIRequest) -> Optional["User"]:
        """Authenticate user which should be assigned to the request."""
        default_value = None
        return self.__run_method_on_plugins("authenticate_user", default_value, request)

    def external_logout(self, plugin_id: str, data: dict, request: WSGIRequest) -> dict:
        """Logout the user."""
        default_value: Dict[str, str] = {}
        plugin = self.get_plugin(plugin_id)
        return self.__run_method_on_single_plugin(
            plugin, "external_logout", default_value, data, request
        )

    def external_verify(
        self, plugin_id: str, data: dict, request: WSGIRequest
    ) -> Tuple[Optional["User"], dict]:
        """Verify the provided authentication data."""
        default_data: Dict[str, str] = dict()
        default_user: Optional["User"] = None
        default_value = default_user, default_data
        plugin = self.get_plugin(plugin_id)
        return self.__run_method_on_single_plugin(
            plugin, "external_verify", default_value, data, request
        )
    
    def perform_mutation(
        self, mutation_cls: Mutation, root, info: ResolveInfo, data: dict
    ) -> Optional[Union[ExecutionResult, GraphQLError]]:
        """Invoke before each mutation is executed.

        This allows to trigger specific logic before the mutation is executed
        but only once the permissions are checked.

        Returns one of:
            - null if the execution shall continue
            - graphql.GraphQLError
            - graphql.execution.ExecutionResult
        """
        return self.__run_method_on_plugins(
            "perform_mutation",
            default_value=None,
            mutation_cls=mutation_cls,
            root=root,
            info=info,
            data=data,
        )

    def is_event_active_for_any_plugin(
        self, event: str, channel_slug: Optional[str] = None
    ) -> bool:
        """Check if any plugin supports defined event."""
        plugins = (
            self.plugins_per_channel[channel_slug] if channel_slug else self.all_plugins
        )
        only_active_plugins = [plugin for plugin in plugins if plugin.active]
        return any([plugin.is_event_active(event) for plugin in only_active_plugins])


def get_plugins_manager(
    requestor_getter: Optional[Callable[[], "Requestor"]] = None
) -> PluginsManager:
    with opentracing.global_tracer().start_active_span("get_plugins_manager"):
        return PluginsManager(settings.PLUGINS, requestor_getter)
