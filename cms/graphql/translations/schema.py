import graphene

from ...core.permissions import SitePermissions
from ...menu.models import MenuItem
from ...page.models import Page
from ...post.models import Post
from ..core.connection import CountableConnection, create_connection_slice
from ..core.fields import ConnectionField, PermissionsField
from ..core.utils import from_global_id_or_error
from ..menu.resolvers import resolve_menu_items
from ..page.resolvers import resolve_pages
from ..post.resolvers import resolve_posts
from ..translations import types as translation_types


TYPES_TRANSLATIONS_MAP = {
    Page: translation_types.PageTranslatableContent,
    Post: translation_types.PostTranslatableContent,
    MenuItem: translation_types.MenuItemTranslatableContent,
}


class TranslatableItem(graphene.Union):
    class Meta:
        types = tuple(TYPES_TRANSLATIONS_MAP.values())

    @classmethod
    def resolve_type(cls, instance, info):
        instance_type = type(instance)
        if instance_type in TYPES_TRANSLATIONS_MAP:
            return TYPES_TRANSLATIONS_MAP[instance_type]

        return super(TranslatableItem, cls).resolve_type(instance, info)


class TranslatableItemConnection(CountableConnection):
    class Meta:
        node = TranslatableItem


class TranslatableKinds(graphene.Enum):
    MENU_ITEM = "MenuItem"
    PAGE = "Page"
    POST = "Post"


class TranslationQueries(graphene.ObjectType):
    translations = ConnectionField(
        TranslatableItemConnection,
        description="Returns a list of all translatable items of a given kind.",
        kind=graphene.Argument(
            TranslatableKinds, required=True, description="Kind of objects to retrieve."
        ),
        permissions=[
            SitePermissions.MANAGE_TRANSLATIONS,
        ],
    )
    translation = PermissionsField(
        TranslatableItem,
        description="Lookup a translatable item by ID.",
        id=graphene.Argument(
            graphene.ID, description="ID of the object to retrieve.", required=True
        ),
        kind=graphene.Argument(
            TranslatableKinds,
            required=True,
            description="Kind of the object to retrieve.",
        ),
        permissions=[SitePermissions.MANAGE_TRANSLATIONS],
    )

    @staticmethod
    def resolve_translations(_root, info, *, kind, **kwargs):
        if kind == TranslatableKinds.PAGE:
            qs = resolve_pages(info)
        elif kind == TranslatableKinds.POST:
            qs = resolve_posts(info)
        elif kind == TranslatableKinds.MENU_ITEM:
            qs = resolve_menu_items(info)

        return create_connection_slice(qs, info, kwargs, TranslatableItemConnection)

    @staticmethod
    def resolve_translation(_root, _info, *, id, kind):
        _type, kind_id = from_global_id_or_error(id)
        if not _type == kind:
            return None
        models = {
            TranslatableKinds.PAGE.value: Page,
            TranslatableKinds.POST.value: Post,
            TranslatableKinds.MENU_ITEM.value: MenuItem,
        }
        return models[kind].objects.filter(pk=kind_id).first()
