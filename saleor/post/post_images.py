import logging
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.templatetags.static import static

from ..thumbnail.models import Thumbnail
from ..thumbnail.utils import get_image_or_proxy_url, get_thumbnail_size

if TYPE_CHECKING:
    from .models import PostMedia


logger = logging.getLogger(__name__)


def get_post_image_thumbnail_url(post_media: Optional["PostMedia"], size: int):
    """Return post media image thumbnail or placeholder if there is no image."""
    size = get_thumbnail_size(size)
    if not post_media or not post_media.image:
        return get_post_image_placeholder(size)
    thumbnail = Thumbnail.objects.filter(size=size, post_media=post_media).first()
    return get_image_or_proxy_url(
        thumbnail, post_media.id, "PostMedia", size, None
    )


def get_post_image_placeholder(size: int):
    """Get a placeholder with the closest size to the provided value."""
    size = get_thumbnail_size(size)
    return static(settings.PLACEHOLDER_IMAGES[size])
