from django.urls import reverse
from django.utils.functional import SimpleLazyObject

from ..graphql.notifications.schema import ExternalNotificationMutations
from .account.schema import AccountMutations, AccountQueries
from .app.schema import AppMutations, AppQueries
from .channel.schema import ChannelMutations, ChannelQueries
from .core.enums import unit_enums
from .core.federation.schema import build_federated_schema
from .core.schema import CoreMutations, CoreQueries
from .menu.schema import MenuMutations, MenuQueries
from .meta.schema import MetaMutations
from .page.schema import PageMutations, PageQueries
from .post.schema import PostMutations, PostQueries
from .plugins.schema import PluginsMutations, PluginsQueries
from .translations.schema import TranslationQueries
from .webhook.schema import WebhookMutations, WebhookQueries
from .webhook.subscription_types import SUBSCRIPTION_EVENTS_TYPES, Subscription

API_PATH = SimpleLazyObject(lambda: reverse("api"))


class Query(
    AccountQueries,
    AppQueries,
    ChannelQueries,
    CoreQueries,
    PluginsQueries,
    MenuQueries,
    PageQueries,
    PostQueries,
    TranslationQueries,
    WebhookQueries,
):
    pass


class Mutation(
    AccountMutations,
    AppMutations,
    ChannelMutations,
    CoreMutations,
    ExternalNotificationMutations,
    PluginsMutations,
    MenuMutations,
    MetaMutations,
    PageMutations,
    PostMutations,
    WebhookMutations,
):
    pass


schema = build_federated_schema(
    Query,
    mutation=Mutation,
    types=unit_enums + SUBSCRIPTION_EVENTS_TYPES,
    subscription=Subscription,
)
