from collections import defaultdict

from promise import Promise

from ...attribute.models import (
    AssignedPostAttribute,
    AssignedPostAttributeValue,
    AttributePost,
)
from ...core.permissions import PostPermissions
from ...post.models import Post, PostType
from ..attribute.dataloaders import AttributesByAttributeId, AttributeValueByIdLoader
from ..core.dataloaders import DataLoader
from ..utils import get_user_or_app_from_context


class PostByIdLoader(DataLoader):
    context_key = "post_by_id"

    def batch_load(self, keys):
        posts = Post.objects.using(self.database_connection_name).in_bulk(keys)
        return [posts.get(post_id) for post_id in keys]


class PostTypeByIdLoader(DataLoader):
    context_key = "post_type_by_id"

    def batch_load(self, keys):
        post_types = PostType.objects.using(self.database_connection_name).in_bulk(keys)
        return [post_types.get(post_type_id) for post_type_id in keys]


class PostsByPostTypeIdLoader(DataLoader):
    """Loads posts by posts type ID."""

    context_key = "posts_by_posttype"

    def batch_load(self, keys):
        posts = Post.objects.using(self.database_connection_name).filter(
            post_type_id__in=keys
        )

        posttype_to_posts = defaultdict(list)
        for post in posts:
            posttype_to_posts[post.post_type_id].append(post)

        return [posttype_to_posts[key] for key in keys]


class PostAttributesByPostTypeIdLoader(DataLoader):
    """Loads post attributes by post type ID."""

    context_key = "post_attributes_by_posttype"

    def batch_load(self, keys):
        requestor = get_user_or_app_from_context(self.context)
        if requestor.is_active and requestor.has_perm(PostPermissions.MANAGE_POSTS):
            qs = AttributePost.objects.using(self.database_connection_name).all()
        else:
            qs = AttributePost.objects.using(self.database_connection_name).filter(
                attribute__visible_in_storefront=True
            )

        post_type_attribute_pairs = qs.filter(post_type_id__in=keys).values_list(
            "post_type_id", "attribute_id"
        )

        post_type_to_attributes_map = defaultdict(list)
        for post_type_id, attr_id in post_type_attribute_pairs:
            post_type_to_attributes_map[post_type_id].append(attr_id)

        def map_attributes(attributes):
            attributes_map = {attr.id: attr for attr in attributes}
            return [
                [
                    attributes_map[attr_id]
                    for attr_id in post_type_to_attributes_map[post_type_id]
                ]
                for post_type_id in keys
            ]

        return (
            AttributesByAttributeId(self.context)
            .load_many(set(attr_id for _, attr_id in post_type_attribute_pairs))
            .then(map_attributes)
        )


class AttributePostsByPostTypeIdLoader(DataLoader):
    """Loads AttributePost objects by post type ID."""

    context_key = "attributeposts_by_posttype"

    def batch_load(self, keys):
        requestor = get_user_or_app_from_context(self.context)
        if requestor.is_active and requestor.has_perm(PostPermissions.MANAGE_POSTS):
            qs = AttributePost.objects.using(self.database_connection_name).all()
        else:
            qs = AttributePost.objects.using(self.database_connection_name).filter(
                attribute__visible_in_storefront=True
            )
        attribute_posts = qs.filter(post_type_id__in=keys)
        posttype_to_attributeposts = defaultdict(list)
        for attribute_post in attribute_posts:
            posttype_to_attributeposts[attribute_post.post_type_id].append(
                attribute_post
            )
        return [posttype_to_attributeposts[key] for key in keys]


class AssignedPostAttributesByPostIdLoader(DataLoader):
    context_key = "assignedpostattributes_by_post"

    def batch_load(self, keys):
        requestor = get_user_or_app_from_context(self.context)
        if requestor.is_active and requestor.has_perm(PostPermissions.MANAGE_POSTS):
            qs = AssignedPostAttribute.objects.using(
                self.database_connection_name
            ).all()
        else:
            qs = AssignedPostAttribute.objects.using(
                self.database_connection_name
            ).filter(assignment__attribute__visible_in_storefront=True)
        assigned_post_attributes = qs.filter(post_id__in=keys)
        post_to_assignedattributes = defaultdict(list)
        for assigned_post_attribute in assigned_post_attributes:
            post_to_assignedattributes[assigned_post_attribute.post_id].append(
                assigned_post_attribute
            )
        return [post_to_assignedattributes[post_id] for post_id in keys]


class AttributeValuesByAssignedPostAttributeIdLoader(DataLoader):
    context_key = "attributevalues_by_assigned_postattribute"

    def batch_load(self, keys):
        attribute_values = AssignedPostAttributeValue.objects.using(
            self.database_connection_name
        ).filter(assignment_id__in=keys)
        value_ids = [a.value_id for a in attribute_values]

        def map_assignment_to_values(values):
            value_map = dict(zip(value_ids, values))
            assigned_post_map = defaultdict(list)
            for attribute_value in attribute_values:
                assigned_post_map[attribute_value.assignment_id].append(
                    value_map.get(attribute_value.value_id)
                )
            return [assigned_post_map[key] for key in keys]

        return (
            AttributeValueByIdLoader(self.context)
            .load_many(value_ids)
            .then(map_assignment_to_values)
        )


class SelectedAttributesByPostIdLoader(DataLoader):
    context_key = "selectedattributes_by_post"

    def batch_load(self, keys):
        def with_posts_and_assigned_attributes(result):
            posts, post_attributes = result
            assigned_post_attributes_ids = list(
                {attr.id for attrs in post_attributes for attr in attrs}
            )
            post_type_ids = [post.post_type_id for post in posts]
            post_attributes = dict(zip(keys, post_attributes))

            def with_attribute_posts_and_values(result):
                attribute_posts, attribute_values = result
                attribute_ids = list(
                    {ap.attribute_id for aps in attribute_posts for ap in aps}
                )
                attribute_posts = dict(zip(post_type_ids, attribute_posts))
                attribute_values = dict(
                    zip(assigned_post_attributes_ids, attribute_values)
                )

                def with_attributes(attributes):
                    id_to_attribute = dict(zip(attribute_ids, attributes))
                    selected_attributes_map = defaultdict(list)
                    for key, post in zip(keys, posts):
                        assigned_posttype_attributes = attribute_posts[
                            post.post_type_id
                        ]
                        assigned_post_attributes = post_attributes[key]
                        for assigned_posttype_attribute in assigned_posttype_attributes:
                            post_assignment = next(
                                (
                                    apa
                                    for apa in assigned_post_attributes
                                    if apa.assignment_id
                                    == assigned_posttype_attribute.id
                                ),
                                None,
                            )
                            attribute = id_to_attribute[
                                assigned_posttype_attribute.attribute_id
                            ]
                            if post_assignment:
                                values = attribute_values[post_assignment.id]
                            else:
                                values = []
                            selected_attributes_map[key].append(
                                {"values": values, "attribute": attribute}
                            )
                    return [selected_attributes_map[key] for key in keys]

                return (
                    AttributesByAttributeId(self.context)
                    .load_many(attribute_ids)
                    .then(with_attributes)
                )

            attribute_posts = AttributePostsByPostTypeIdLoader(self.context).load_many(
                post_type_ids
            )
            attribute_values = AttributeValuesByAssignedPostAttributeIdLoader(
                self.context
            ).load_many(assigned_post_attributes_ids)
            return Promise.all([attribute_posts, attribute_values]).then(
                with_attribute_posts_and_values
            )

        posts = PostByIdLoader(self.context).load_many(keys)
        assigned_attributes = AssignedPostAttributesByPostIdLoader(
            self.context
        ).load_many(keys)

        return Promise.all([posts, assigned_attributes]).then(
            with_posts_and_assigned_attributes
        )
