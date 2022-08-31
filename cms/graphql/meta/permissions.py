from typing import Any, List

from django.core.exceptions import ValidationError

from ...account import models as account_models
from ...account.error_codes import AccountErrorCode
from ...core.exceptions import PermissionDenied
from ...core.jwt import JWT_THIRDPARTY_ACCESS_TYPE
from ...core.permissions import (
    AccountPermissions,
    AppPermission,
    BasePermissionEnum,
    MenuPermissions,
    PagePermissions,
    PageTypePermissions,
    PostPermissions,
    PostTypePermissions,
)
from ..core.utils import from_global_id_or_error


def no_permissions(_info, _object_pk: Any) -> List[None]:
    return []


def public_user_permissions(info, user_pk: int) -> List[BasePermissionEnum]:
    """Resolve permission for access to public metadata for user.

    Customer have access to own public metadata.
    Staff user with `MANAGE_USERS` have access to customers public metadata.
    Staff user with `MANAGE_STAFF` have access to staff users public metadata.
    """
    user = account_models.User.objects.filter(pk=user_pk).first()
    if not user:
        raise ValidationError(
            {
                "id": ValidationError(
                    "Couldn't resolve user.", code=AccountErrorCode.NOT_FOUND.value
                )
            }
        )
    if info.context.user.pk == user.pk:
        return []
    if user.is_staff:
        return [AccountPermissions.MANAGE_STAFF]
    return [AccountPermissions.MANAGE_USERS]


def private_user_permissions(_info, user_pk: int) -> List[BasePermissionEnum]:
    user = account_models.User.objects.filter(pk=user_pk).first()
    if not user:
        raise PermissionDenied()
    if user.is_staff:
        return [AccountPermissions.MANAGE_STAFF]
    return [AccountPermissions.MANAGE_USERS]


def menu_permissions(_info, _object_pk: Any) -> List[BasePermissionEnum]:
    return [MenuPermissions.MANAGE_MENUS]


def app_permissions(info, object_pk: str) -> List[BasePermissionEnum]:
    auth_token = info.context.decoded_auth_token or {}
    if auth_token.get("type") == JWT_THIRDPARTY_ACCESS_TYPE:
        _, app_id = from_global_id_or_error(auth_token["app"], "App")
    else:
        app_id = info.context.app.id if info.context.app else None
    if app_id is not None and int(app_id) == int(object_pk):
        return []
    return [AppPermission.MANAGE_APPS]


def private_app_permssions(info, object_pk: str) -> List[BasePermissionEnum]:
    app = info.context.app
    if app and app.pk == int(object_pk):
        return []
    return [AppPermission.MANAGE_APPS]


def page_permissions(_info, _object_pk: Any) -> List[BasePermissionEnum]:
    return [PagePermissions.MANAGE_PAGES]


def page_type_permissions(_info, _object_pk: Any) -> List[BasePermissionEnum]:
    return [PageTypePermissions.MANAGE_PAGE_TYPES_AND_ATTRIBUTES]


def post_permissions(_info, _object_pk: Any) -> List[BasePermissionEnum]:
    return [PostPermissions.MANAGE_POSTS]


def post_type_permissions(_info, _object_pk: Any) -> List[BasePermissionEnum]:
    return [PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES]


PUBLIC_META_PERMISSION_MAP = {
    "App": app_permissions,
    "Menu": menu_permissions,
    "MenuItem": menu_permissions,
    "Page": page_permissions,
    "PageType": page_type_permissions,
    "Post": post_permissions,
    "PostType": post_type_permissions,
    "User": public_user_permissions,
}


PRIVATE_META_PERMISSION_MAP = {
    "App": private_app_permssions,    
    "Menu": menu_permissions,
    "MenuItem": menu_permissions,    
    "Page": page_permissions,
    "PageType": page_type_permissions,
    "Post": post_permissions,
    "PostType": post_type_permissions,
    "User": private_user_permissions,
}
