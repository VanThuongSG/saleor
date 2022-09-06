import django_filters
from django.db.models import Exists, Q, OuterRef

from ...post import models
from ..core.filters import GlobalIDMultipleChoiceFilter, MetadataFilterBase
from ..core.types import FilterInputObjectType
from ..utils import resolve_global_ids_to_primary_keys
from ..utils.filters import filter_by_id
from .types import Post, PostType, Category
# from . import types as product_types

def filter_post_search(qs, _, value):
    if not value:
        return qs
    return qs.filter(
        Q(title__trigram_similar=value)
        | Q(slug__trigram_similar=value)
        | Q(content__icontains=value)
    )


def filter_post_post_types(qs, _, value):
    if not value:
        return qs
    _, post_types_pks = resolve_global_ids_to_primary_keys(value, PostType)
    return qs.filter(post_type_id__in=post_types_pks)


def filter_post_type_search(qs, _, value):
    if not value:
        return qs
    return qs.filter(Q(name__trigram_similar=value) | Q(slug__trigram_similar=value))


def filter_categories(qs, _, value):
    if value:
        _, category_pks = resolve_global_ids_to_primary_keys(
            value, Category
        )
        qs = filter_posts_by_categories(qs, category_pks)
    return qs


def filter_posts_by_categories(qs, category_ids):
    categories = models.Category.objects.filter(pk__in=category_ids)
    categories = models.Category.tree.get_queryset_descendants(
        categories, include_self=True
    ).values("pk")
    return qs.filter(Exists(categories.filter(pk=OuterRef("category_id"))))


def filter_has_category(qs, _, value):
    return qs.filter(category__isnull=not value)


class CategoryFilter(MetadataFilterBase):
    search = django_filters.CharFilter(method="category_filter_search")
    ids = GlobalIDMultipleChoiceFilter(field_name="id")

    class Meta:
        model = models.Category
        fields = ["search"]

    @classmethod
    def category_filter_search(cls, queryset, _name, value):
        if not value:
            return queryset
        name_slug_desc_qs = (
            Q(name__ilike=value)
            | Q(slug__ilike=value)
            | Q(description_plaintext__ilike=value)
        )

        return queryset.filter(name_slug_desc_qs)


class PostFilter(MetadataFilterBase):
    is_published = django_filters.BooleanFilter(method="filter_is_published")
    search = django_filters.CharFilter(method=filter_post_search)
    post_types = GlobalIDMultipleChoiceFilter(method=filter_post_post_types)
    categories = GlobalIDMultipleChoiceFilter(method=filter_categories)
    has_category = django_filters.BooleanFilter(method=filter_has_category)
    ids = GlobalIDMultipleChoiceFilter(method=filter_by_id(models.Post))

    class Meta:
        model = models.Post
        fields = [
            "is_published",
            "categories",
            "has_category",
            "search"
        ]


class PostFilterInput(FilterInputObjectType):
    class Meta:
        filterset_class = PostFilter


class PostTypeFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method=filter_post_type_search)


class PostTypeFilterInput(FilterInputObjectType):
    class Meta:
        filterset_class = PostTypeFilter


class CategoryFilterInput(FilterInputObjectType):
    class Meta:
        filterset_class = CategoryFilter