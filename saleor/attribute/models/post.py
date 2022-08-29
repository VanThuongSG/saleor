from django.db import models

from ...core.models import SortableModel
from ...post.models import Post, PostType
from .base import AssociatedAttributeQuerySet, BaseAssignedAttribute


class AssignedPostAttributeValue(SortableModel):
    value = models.ForeignKey(
        "AttributeValue",
        on_delete=models.CASCADE,
        related_name="postvalueassignment",
    )
    assignment = models.ForeignKey(
        "AssignedPostAttribute",
        on_delete=models.CASCADE,
        related_name="postvalueassignment",
    )

    class Meta:
        unique_together = (("value", "assignment"),)
        ordering = ("sort_order", "pk")

    def get_ordering_queryset(self):
        return self.assignment.postvalueassignment.all()


class AssignedPostAttribute(BaseAssignedAttribute):
    """Associate a post type attribute and selected values to a given post."""

    post = models.ForeignKey(Post, related_name="attributes", on_delete=models.CASCADE)
    assignment = models.ForeignKey(
        "AttributePost", on_delete=models.CASCADE, related_name="postassignments"
    )
    values = models.ManyToManyField(
        "AttributeValue",
        blank=True,
        related_name="postassignments",
        through=AssignedPostAttributeValue,
    )

    class Meta:
        unique_together = (("post", "assignment"),)


class AttributePost(SortableModel):
    attribute = models.ForeignKey(
        "Attribute", related_name="attributepost", on_delete=models.CASCADE
    )
    post_type = models.ForeignKey(
        PostType, related_name="attributepost", on_delete=models.CASCADE
    )
    assigned_posts = models.ManyToManyField(
        Post,
        blank=True,
        through=AssignedPostAttribute,
        through_fields=("assignment", "post"),
        related_name="attributesrelated",
    )

    objects = models.Manager.from_queryset(AssociatedAttributeQuerySet)()

    class Meta:
        unique_together = (("attribute", "post_type"),)
        ordering = ("sort_order", "pk")

    def get_ordering_queryset(self):
        return self.post_type.attributepost.all()
