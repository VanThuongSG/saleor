import graphene
from django.conf import settings

from ...account import error_codes as account_error_codes
from ...app import error_codes as app_error_codes
from ...channel import error_codes as channel_error_codes
from ...core import JobStatus, TimePeriodType
from ...core import error_codes as core_error_codes
from ...core.permissions import get_permissions_enum_list

from ...menu import error_codes as menu_error_codes
from ...page import error_codes as page_error_codes
from ...post import error_codes as post_error_codes
from ...plugins import error_codes as plugin_error_codes
from ...site import error_codes as site_error_codes
from ...thumbnail import ThumbnailFormat
from ...webhook import error_codes as webhook_error_codes
from ..notifications import error_codes as external_notifications_error_codes
from .utils import str_to_enum


class OrderDirection(graphene.Enum):
    ASC = ""
    DESC = "-"

    @property
    def description(self):
        # Disable all the no-member violations in this function
        # pylint: disable=no-member
        if self == OrderDirection.ASC:
            return "Specifies an ascending sort order."
        if self == OrderDirection.DESC:
            return "Specifies a descending sort order."
        raise ValueError("Unsupported enum value: %s" % self.value)


class ReportingPeriod(graphene.Enum):
    TODAY = "TODAY"
    THIS_MONTH = "THIS_MONTH"


def to_enum(enum_cls, *, type_name=None, **options) -> graphene.Enum:
    """Create a Graphene enum from a class containing a set of options.

    :param enum_cls:
        The class to build the enum from.
    :param type_name:
        The name of the type. Default is the class name + 'Enum'.
    :param options:
        - description:
            Contains the type description (default is the class's docstring)
        - deprecation_reason:
            Contains the deprecation reason.
            The default is enum_cls.__deprecation_reason__ or None.
    :return:
    """

    # note this won't work until
    # https://github.com/graphql-python/graphene/issues/956 is fixed
    deprecation_reason = getattr(enum_cls, "__deprecation_reason__", None)
    if deprecation_reason:
        options.setdefault("deprecation_reason", deprecation_reason)

    type_name = type_name or (enum_cls.__name__ + "Enum")
    enum_data = [(str_to_enum(code.upper()), code) for code, name in enum_cls.CHOICES]
    return graphene.Enum(type_name, enum_data, **options)


LanguageCodeEnum = graphene.Enum(
    "LanguageCodeEnum",
    [(lang[0].replace("-", "_").upper(), lang[0]) for lang in settings.LANGUAGES],
)


JobStatusEnum = to_enum(JobStatus)
PermissionEnum = graphene.Enum("PermissionEnum", get_permissions_enum_list())
TimePeriodTypeEnum = to_enum(TimePeriodType)
ThumbnailFormatEnum = to_enum(ThumbnailFormat)

AccountErrorCode = graphene.Enum.from_enum(account_error_codes.AccountErrorCode)
AppErrorCode = graphene.Enum.from_enum(app_error_codes.AppErrorCode)
ChannelErrorCode = graphene.Enum.from_enum(channel_error_codes.ChannelErrorCode)

ExternalNotificationTriggerErrorCode = graphene.Enum.from_enum(
    external_notifications_error_codes.ExternalNotificationErrorCodes
)
PluginErrorCode = graphene.Enum.from_enum(plugin_error_codes.PluginErrorCode)
MenuErrorCode = graphene.Enum.from_enum(menu_error_codes.MenuErrorCode)
OrderSettingsErrorCode = graphene.Enum.from_enum(
    site_error_codes.OrderSettingsErrorCode
)
GiftCardSettingsErrorCode = graphene.Enum.from_enum(
    site_error_codes.GiftCardSettingsErrorCode
)
MetadataErrorCode = graphene.Enum.from_enum(core_error_codes.MetadataErrorCode)
PageErrorCode = graphene.Enum.from_enum(page_error_codes.PageErrorCode)
PostErrorCode = graphene.Enum.from_enum(post_error_codes.PostErrorCode)
PermissionGroupErrorCode = graphene.Enum.from_enum(
    account_error_codes.PermissionGroupErrorCode
)
ShopErrorCode = graphene.Enum.from_enum(core_error_codes.ShopErrorCode)
UploadErrorCode = graphene.Enum.from_enum(core_error_codes.UploadErrorCode)
WebhookErrorCode = graphene.Enum.from_enum(webhook_error_codes.WebhookErrorCode)
TranslationErrorCode = graphene.Enum.from_enum(core_error_codes.TranslationErrorCode)
