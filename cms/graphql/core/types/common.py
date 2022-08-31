from urllib.parse import urljoin

import graphene
from django.conf import settings

from ....core.tracing import traced_resolver
from ..descriptions import ADDED_IN_36, PREVIEW_FEATURE
from ..enums import (
    AccountErrorCode,
    AppErrorCode,
    ChannelErrorCode,
    ExternalNotificationTriggerErrorCode,
    JobStatusEnum,
    LanguageCodeEnum,
    MenuErrorCode,
    MetadataErrorCode,
    OrderSettingsErrorCode,
    PageErrorCode,
    PermissionEnum,
    PermissionGroupErrorCode,
    PostErrorCode,
    PluginErrorCode,
    ShopErrorCode,
    ThumbnailFormatEnum,
    TimePeriodTypeEnum,
    TranslationErrorCode,
    UploadErrorCode,
    WebhookErrorCode,
)
from ..scalars import PositiveDecimal


class NonNullList(graphene.List):
    """A list type that automatically adds non-null constraint on contained items."""

    def __init__(self, of_type, *args, **kwargs):
        of_type = graphene.NonNull(of_type)
        super(NonNullList, self).__init__(of_type, *args, **kwargs)


class LanguageDisplay(graphene.ObjectType):
    code = LanguageCodeEnum(
        description="ISO 639 representation of the language name.", required=True
    )
    language = graphene.String(description="Full name of the language.", required=True)


class Permission(graphene.ObjectType):
    code = PermissionEnum(description="Internal code for permission.", required=True)
    name = graphene.String(
        description="Describe action(s) allowed to do by permission.", required=True
    )

    class Meta:
        description = "Represents a permission object in a friendly form."


class Error(graphene.ObjectType):
    field = graphene.String(
        description=(
            "Name of a field that caused the error. A value of `null` indicates that "
            "the error isn't associated with a particular field."
        ),
        required=False,
    )
    message = graphene.String(description="The error message.")

    class Meta:
        description = "Represents an error in the input of a mutation."


class AccountError(Error):
    code = AccountErrorCode(description="The error code.", required=True)


class AppError(Error):
    code = AppErrorCode(description="The error code.", required=True)
    permissions = NonNullList(
        PermissionEnum,
        description="List of permissions which causes the error.",
        required=False,
    )


class StaffError(AccountError):
    permissions = NonNullList(
        PermissionEnum,
        description="List of permissions which causes the error.",
        required=False,
    )
    groups = NonNullList(
        graphene.ID,
        description="List of permission group IDs which cause the error.",
        required=False,
    )
    users = NonNullList(
        graphene.ID,
        description="List of user IDs which causes the error.",
        required=False,
    )


class ChannelError(Error):
    code = ChannelErrorCode(description="The error code.", required=True)


class ExternalNotificationError(Error):
    code = ExternalNotificationTriggerErrorCode(
        description="The error code.", required=True
    )


class MenuError(Error):
    code = MenuErrorCode(description="The error code.", required=True)


class OrderSettingsError(Error):
    code = OrderSettingsErrorCode(description="The error code.", required=True)


class MetadataError(Error):
    code = MetadataErrorCode(description="The error code.", required=True)


class PermissionGroupError(Error):
    code = PermissionGroupErrorCode(description="The error code.", required=True)
    permissions = NonNullList(
        PermissionEnum,
        description="List of permissions which causes the error.",
        required=False,
    )
    users = NonNullList(
        graphene.ID,
        description="List of user IDs which causes the error.",
        required=False,
    )


class ShopError(Error):
    code = ShopErrorCode(description="The error code.", required=True)


class PageError(Error):
    code = PageErrorCode(description="The error code.", required=True)
    attributes = NonNullList(
        graphene.ID,
        description="List of attributes IDs which causes the error.",
        required=False,
    )
    values = NonNullList(
        graphene.ID,
        description="List of attribute values IDs which causes the error.",
        required=False,
    )


class PostError(Error):
    code = PostErrorCode(description="The error code.", required=True)
    attributes = NonNullList(
        graphene.ID,
        description="List of attributes IDs which causes the error.",
        required=False,
    )
    values = NonNullList(
        graphene.ID,
        description="List of attribute values IDs which causes the error.",
        required=False,
    )


class PluginError(Error):
    code = PluginErrorCode(description="The error code.", required=True)


class UploadError(Error):
    code = UploadErrorCode(description="The error code.", required=True)


class WebhookError(Error):
    code = WebhookErrorCode(description="The error code.", required=True)


class TranslationError(Error):
    code = TranslationErrorCode(description="The error code.", required=True)


class SeoInput(graphene.InputObjectType):
    title = graphene.String(description="SEO title.")
    description = graphene.String(description="SEO description.")


class Image(graphene.ObjectType):
    url = graphene.String(required=True, description="The URL of the image.")
    alt = graphene.String(description="Alt text for an image.")

    class Meta:
        description = "Represents an image."

    @staticmethod
    def resolve_url(root, info):
        return info.context.build_absolute_uri(urljoin(settings.MEDIA_URL, root.url))


class File(graphene.ObjectType):
    url = graphene.String(required=True, description="The URL of the file.")
    content_type = graphene.String(
        required=False, description="Content type of the file."
    )

    @staticmethod
    def resolve_url(root, info):
        return info.context.build_absolute_uri(urljoin(settings.MEDIA_URL, root.url))


class DateRangeInput(graphene.InputObjectType):
    gte = graphene.Date(description="Start date.", required=False)
    lte = graphene.Date(description="End date.", required=False)


class DateTimeRangeInput(graphene.InputObjectType):
    gte = graphene.DateTime(description="Start date.", required=False)
    lte = graphene.DateTime(description="End date.", required=False)


class IntRangeInput(graphene.InputObjectType):
    gte = graphene.Int(description="Value greater than or equal to.", required=False)
    lte = graphene.Int(description="Value less than or equal to.", required=False)


class TimePeriodInputType(graphene.InputObjectType):
    amount = graphene.Int(description="The length of the period.", required=True)
    type = TimePeriodTypeEnum(description="The type of the period.", required=True)


class Job(graphene.Interface):
    status = JobStatusEnum(description="Job status.", required=True)
    created_at = graphene.DateTime(
        description="Created date time of job in ISO 8601 format.", required=True
    )
    updated_at = graphene.DateTime(
        description="Date time of job last update in ISO 8601 format.", required=True
    )
    message = graphene.String(description="Job message.")

    @classmethod
    @traced_resolver
    def resolve_type(cls, instance, _info):
        """Map a data object to a Graphene type."""
        MODEL_TO_TYPE_MAP = {
            # <DjangoModel>: <GrapheneType>
        }
        return MODEL_TO_TYPE_MAP.get(type(instance))


class TimePeriod(graphene.ObjectType):
    amount = graphene.Int(description="The length of the period.", required=True)
    type = TimePeriodTypeEnum(description="The type of the period.", required=True)


class ThumbnailField(graphene.Field):
    size = graphene.Int(
        description=(
            "Size of the image. If not provided, the original image "
            "will be returned."
        )
    )
    format = ThumbnailFormatEnum(
        description=(
            "The format of the image. When not provided, format of the original "
            "image will be used. Must be provided together with the size value, "
            "otherwise original image will be returned." + ADDED_IN_36 + PREVIEW_FEATURE
        )
    )

    def __init__(self, of_type=Image, *args, **kwargs):
        kwargs["size"] = self.size
        kwargs["format"] = self.format
        super().__init__(of_type, *args, **kwargs)
