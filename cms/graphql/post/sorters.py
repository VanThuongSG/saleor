import graphene
from django.db.models import (
    Count,
    IntegerField,
    OuterRef,
    QuerySet,
    Subquery,
)
from django.db.models.functions import Coalesce

from ...post.models import Category, Post

from ..core.descriptions import DEPRECATED_IN_3X_INPUT
from ..core.types import SortInputObjectType


class PostSortField(graphene.Enum):
    TITLE = ["title", "slug"]
    SLUG = ["slug"]
    VISIBILITY = ["is_published", "title", "slug"]
    CREATION_DATE = ["created_at", "title", "slug"]
    PUBLICATION_DATE = ["published_at", "title", "slug"]
    PUBLISHED_AT = ["published_at", "title", "slug"]

    @property
    def description(self):
        if self.name in PostSortField.__enum__._member_names_:
            sort_name = self.name.lower().replace("_", " ")
            description = f"Sort posts by {sort_name}."
            if self.name == "PUBLICATION_DATE":
                description += DEPRECATED_IN_3X_INPUT
            return description
        raise ValueError("Unsupported enum value: %s" % self.value)


class PostSortingInput(SortInputObjectType):
    class Meta:
        sort_enum = PostSortField
        type_name = "posts"


class PostTypeSortField(graphene.Enum):
    NAME = ["name", "slug"]
    SLUG = ["slug"]

    @property
    def description(self):
        if self.name in PostTypeSortField.__enum__._member_names_:
            sport_name = self.name.lower().replace("_", " ")
            return f"Sort post types by {sport_name}."
        raise ValueError(f"Unsupported enum value: {self.value}")


class PostTypeSortingInput(SortInputObjectType):
    class Meta:
        sort_enum = PostTypeSortField
        type_name = "post types"


class CategorySortField(graphene.Enum):
    NAME = ["name", "slug"]
    POST_COUNT = ["post_count", "name", "slug"]
    SUBCATEGORY_COUNT = ["subcategory_count", "name", "slug"]

    @property
    def description(self):
        # pylint: disable=no-member
        if self in [
            CategorySortField.NAME,
            CategorySortField.POST_COUNT,
            CategorySortField.SUBCATEGORY_COUNT,
        ]:
            sort_name = self.name.lower().replace("_", " ")
            return f"Sort categories by {sort_name}."
        raise ValueError("Unsupported enum value: %s" % self.value)

    @staticmethod
    def qs_with_post_count(queryset: QuerySet, **_kwargs) -> QuerySet:
        return queryset.annotate(
            post_count=Coalesce(
                Subquery(
                    Category.tree.add_related_count(
                        queryset, Post, "category", "p_c", cumulative=True
                    )
                    .values("p_c")
                    .filter(pk=OuterRef("pk"))[:1]
                ),
                0,
                output_field=IntegerField(),
            )
        )

    @staticmethod
    def qs_with_subcategory_count(queryset: QuerySet, **_kwargs) -> QuerySet:
        return queryset.annotate(subcategory_count=Count("children__id"))


class CategorySortingInput(SortInputObjectType):
    class Meta:
        sort_enum = CategorySortField
        type_name = "categories"