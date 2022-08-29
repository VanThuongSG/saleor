import django_filters
from django.db.models import Q

from ...post import models
from ..core.filters import GlobalIDMultipleChoiceFilter, MetadataFilterBase
from ..core.types import FilterInputObjectType
from ..utils import resolve_global_ids_to_primary_keys
from ..utils.filters import filter_by_id
from .types import Post, PostType


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


class PostFilter(MetadataFilterBase):
    search = django_filters.CharFilter(method=filter_post_search)
    post_types = GlobalIDMultipleChoiceFilter(method=filter_post_post_types)
    ids = GlobalIDMultipleChoiceFilter(method=filter_by_id(Post))

    class Meta:
        model = models.Post
        fields = ["search"]


class PostFilterInput(FilterInputObjectType):
    class Meta:
        filterset_class = PostFilter


class PostTypeFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method=filter_post_type_search)


class PostTypeFilterInput(FilterInputObjectType):
    class Meta:
        filterset_class = PostTypeFilter
