import graphene

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
