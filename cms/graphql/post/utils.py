from collections import defaultdict
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction

from ..core.enums import PostErrorCode


import logging

logger = logging.getLogger(__name__)


def update_ordered_media(ordered_media):
    errors = defaultdict(list)
    with transaction.atomic():
        for order, media in enumerate(ordered_media):
            media.sort_order = order
            try:
                media.save(update_fields=["sort_order"])
            except DatabaseError as e:
                msg = (
                    "Cannot update media for instance: %s. "
                    "Updating not existing object. "
                    "Details: %s.",
                    media,
                    str(e),
                )
                logger.warning(msg)
                errors["media"].append(
                    ValidationError(msg, code=PostErrorCode.NOT_FOUND.value)
                )

    if errors:
        raise ValidationError(errors)
