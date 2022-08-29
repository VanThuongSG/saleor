from django.contrib.postgres.indexes import GinIndex
from django.db import models

from ..core.db.fields import SanitizedJSONField
from ..core.models import ModelWithMetadata, PublishableModel, PublishedQuerySet
from ..core.permissions import PostPermissions, PostTypePermissions
from ..core.utils.editorjs import clean_editor_js
from ..core.utils.translations import TranslationProxy
from ..seo.models import SeoModel, SeoModelTranslation


class PostQueryset(PublishedQuerySet):
    def visible_to_user(self, requestor):
        if requestor.has_perm(PostPermissions.MANAGE_POSTS):
            return self.all()
        return self.published()


class Post(ModelWithMetadata, SeoModel, PublishableModel):
    slug = models.SlugField(unique=True, max_length=255)
    title = models.CharField(max_length=250)
    post_type = models.ForeignKey(
        "PostType", related_name="posts", on_delete=models.CASCADE
    )
    content = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)
    created_at = models.DateTimeField(auto_now_add=True)

    # external_url = models.URLField(blank=True, null=True, max_length=2048)

    translated = TranslationProxy()

    objects = models.Manager.from_queryset(PostQueryset)()

    class Meta(ModelWithMetadata.Meta):
        ordering = ("slug",)
        permissions = ((PostPermissions.MANAGE_POSTS.codename, "Manage posts."),)
        indexes = [*ModelWithMetadata.Meta.indexes, GinIndex(fields=["title", "slug"])]

    def __str__(self):
        return self.title


class PostTranslation(SeoModelTranslation):
    post = models.ForeignKey(
        Post, related_name="translations", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    content = SanitizedJSONField(blank=True, null=True, sanitizer=clean_editor_js)

    class Meta:
        ordering = ("language_code", "post", "pk")
        unique_together = (("language_code", "post"),)

    def __repr__(self):
        class_ = type(self)
        return "%s(pk=%r, title=%r, post_pk=%r)" % (
            class_.__name__,
            self.pk,
            self.title,
            self.post_id,
        )

    def __str__(self):
        return self.title if self.title else str(self.pk)

    def get_translated_object_id(self):
        return "Post", self.post_id

    def get_translated_keys(self):
        translated_keys = super().get_translated_keys()
        translated_keys.update(
            {
                "title": self.title,
                "content": self.content,
            }
        )
        return translated_keys


class PostType(ModelWithMetadata):
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)

    class Meta(ModelWithMetadata.Meta):
        ordering = ("slug",)
        permissions = (
            (
                PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES.codename,
                "Manage post types and attributes.",
            ),
        )
        indexes = [*ModelWithMetadata.Meta.indexes, GinIndex(fields=["name", "slug"])]
