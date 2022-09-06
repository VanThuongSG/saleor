import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import datetime

import graphene
import pytz
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import transaction

from ....core.permissions import PostPermissions, PostTypePermissions
from ....core.tasks import delete_post_media_task
from ....core.tracing import traced_atomic_transaction
from ....core.utils.editorjs import clean_editor_js
from ....core.utils.validators import get_oembed_data
from ....post import PostMediaTypes, models
from ....post.error_codes import PostErrorCode
from ....post.utils import delete_categories
from ....thumbnail import models as thumbnail_models
from ...core.descriptions import ADDED_IN_33, DEPRECATED_IN_3X_INPUT, RICH_CONTENT
from ...core.fields import JSONString
from ...core.mutations import ModelDeleteMutation, ModelMutation, BaseMutation
from ...core.types import NonNullList, PostError, SeoInput, Upload
from ...core.utils import (
    add_hash_to_file_name,
    clean_seo_fields,
    get_filename_from_url,
    validate_slug_and_generate_if_needed,
    is_image_url,
    validate_image_file,
    validate_image_url,
)
from ...utils.validators import check_for_duplicates
from ..types import Post, PostType, PostMedia, Category
from ..utils import update_ordered_media


class CategoryInput(graphene.InputObjectType):
    description = JSONString(description="Category description." + RICH_CONTENT)
    name = graphene.String(description="Category name.")
    slug = graphene.String(description="Category slug.")
    seo = SeoInput(description="Search engine optimization fields.")
    background_image = Upload(description="Background image file.")
    background_image_alt = graphene.String(description="Alt text for a post media.")


class CategoryCreate(ModelMutation):
    class Arguments:
        input = CategoryInput(
            required=True, description="Fields required to create a category."
        )
        parent_id = graphene.ID(
            description=(
                "ID of the parent category. If empty, category will be top level "
                "category."
            ),
            name="parent",
        )

    class Meta:
        description = "Creates a new category."
        model = models.Category
        object_type = Category
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def clean_input(cls, info, instance, data):
        cleaned_input = super().clean_input(info, instance, data)
        description = cleaned_input.get("description")
        cleaned_input["description_plaintext"] = (
            clean_editor_js(description, to_string=True) if description else ""
        )
        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "name", cleaned_input
            )
        except ValidationError as error:
            error.code = PostErrorCode.REQUIRED.value
            raise ValidationError({"slug": error})
        parent_id = data["parent_id"]
        if parent_id:
            parent = cls.get_node_or_error(
                info, parent_id, field="parent", only_type=Category
            )
            cleaned_input["parent"] = parent
        if data.get("background_image"):
            image_data = info.context.FILES.get(data["background_image"])
            validate_image_file(image_data, "background_image", PostErrorCode)
            add_hash_to_file_name(image_data)
        clean_seo_fields(cleaned_input)
        return cleaned_input

    @classmethod
    def perform_mutation(cls, root, info, **data):
        parent_id = data.pop("parent_id", None)
        data["input"]["parent_id"] = parent_id
        return super().perform_mutation(root, info, **data)

    @classmethod
    def post_save_action(cls, info, instance, _cleaned_input):
        info.context.plugins.category_created(instance)


class CategoryUpdate(CategoryCreate):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a category to update.")
        input = CategoryInput(
            required=True, description="Fields required to update a category."
        )

    class Meta:
        description = "Updates a category."
        model = models.Category
        object_type = Category
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def construct_instance(cls, instance, cleaned_data):
        # delete old background image and related thumbnails
        if "background_image" in cleaned_data and instance.background_image:
            instance.background_image.delete()
            thumbnail_models.Thumbnail.objects.filter(category_id=instance.id).delete()
        return super().construct_instance(instance, cleaned_data)

    @classmethod
    def post_save_action(cls, info, instance, _cleaned_input):
        info.context.plugins.category_updated(instance)


class CategoryDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a category to delete.")

    class Meta:
        description = "Deletes a category."
        model = models.Category
        object_type = Category
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        node_id = data.get("id")
        instance = cls.get_node_or_error(info, node_id, only_type=Category)

        db_id = instance.id

        delete_categories([db_id], manager=info.context.plugins)

        instance.id = db_id
        return cls.success_response(instance)


class PostInput(graphene.InputObjectType):
    category = graphene.ID(description="ID of the product's category.", name="category")
    slug = graphene.String(description="Post internal name.")
    title = graphene.String(description="Post title.")
    content = JSONString(description="Post content." + RICH_CONTENT)
    is_published = graphene.Boolean(
        description="Determines if post is visible in the storefront."
    )
    publication_date = graphene.String(
        description=(
            f"Publication date. ISO 8601 standard. {DEPRECATED_IN_3X_INPUT} "
            "Use `publishedAt` field instead."
        )
    )
    published_at = graphene.DateTime(
        description="Publication date time. ISO 8601 standard." + ADDED_IN_33
    )
    seo = SeoInput(description="Search engine optimization fields.")
    external_url = graphene.String(description="Th original post url.")


class PostCreateInput(PostInput):
    post_type = graphene.ID(
        description="ID of the post type that post belongs to.", required=True
    )


class PostCreate(ModelMutation):
    class Arguments:
        input = PostCreateInput(
            required=True, description="Fields required to create a post."
        )

    class Meta:
        description = "Creates a new post."
        model = models.Post
        object_type = Post
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"


    @classmethod
    def clean_input(cls, info, instance, data):
        cleaned_input = super().clean_input(info, instance, data)
        external_url = cleaned_input.get("external_url")

        r = requests.get(external_url)
        soup = BeautifulSoup(r.text)
        meta = soup.findAll('meta')

        external_description = ""
        external_title = ""
        seo_data = {
            "title": "",
            "description": ""
        }

        for tag in meta:            
            if 'name' in tag.attrs.keys() and tag.attrs['name'].strip().lower() in ['description']:
                external_description = tag.attrs['content']
            if 'name' in tag.attrs.keys() and tag.attrs['name'].strip().lower() in ['title']:
                external_title = tag.attrs['content']
            if 'property' in tag.attrs.keys() and tag.attrs['property'].strip().lower() in ['og:image']:
                print(tag.attrs['content'])
                cleaned_input["featured_image"] = tag.attrs['content']
        
        # Populate external data if available
        if external_description:
            description_editorjs = {
                # "time": 1607174917790,
                "blocks": [
                {
                    "data": {
                        "text": external_description
                    },
                    "type": "paragraph"
                }
                ],
                "version": "2.22.2"
            }
            cleaned_input["content"] = description_editorjs
            seo_data["description"] = external_description

        if external_title:
            cleaned_input["title"] = external_title
            seo_data["title"] = external_title
        
        cleaned_input["seo"] = seo_data

        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "title", cleaned_input
            )
        except ValidationError as error:
            error.code = PostErrorCode.REQUIRED
            raise ValidationError({"slug": error})

        if "publication_date" in cleaned_input and "published_at" in cleaned_input:
            raise ValidationError(
                {
                    "publication_date": ValidationError(
                        "Only one of argument: publicationDate or publishedAt "
                        "must be specified.",
                        code=PostErrorCode.INVALID.value,
                    )
                }
            )

        is_published = cleaned_input.get("is_published")
        publication_date = cleaned_input.get("published_at") or cleaned_input.get(
            "publication_date"
        )
        if is_published and not publication_date:
            cleaned_input["published_at"] = datetime.now(pytz.UTC)
        elif "publication_date" in cleaned_input or "published_at" in cleaned_input:
            cleaned_input["published_at"] = publication_date

        clean_seo_fields(cleaned_input)
        return cleaned_input

    @classmethod
    @traced_atomic_transaction()
    def _save_m2m(cls, info, instance, cleaned_data):
        super()._save_m2m(info, instance, cleaned_data)

    @classmethod
    def save(cls, info, instance, cleaned_input):
        super().save(info, instance, cleaned_input)
        media_url = cleaned_input.get("featured_image")
        if media_url:
            if is_image_url(media_url):
                validate_image_url(media_url, "media_url", PostErrorCode.INVALID)
                filename = get_filename_from_url(media_url)
                image_data = requests.get(media_url, stream=True)
                image_file = File(image_data.raw, filename)                
                instance.media.create(
                    image=image_file,
                    alt="Default image alt",
                    type=PostMediaTypes.IMAGE,
                )
        info.context.plugins.post_created(instance)


class PostUpdate(PostCreate):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a post to update.")
        input = PostInput(
            required=True, description="Fields required to update a post."
        )

    class Meta:
        description = "Updates an existing post."
        model = models.Post
        object_type = Post
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"


    @classmethod
    def save(cls, info, instance, cleaned_input):
        super(PostCreate, cls).save(info, instance, cleaned_input)
        info.context.plugins.post_updated(instance)


class PostDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of a post to delete.")

    class Meta:
        description = "Deletes a post."
        model = models.Post
        object_type = Post
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    @traced_atomic_transaction()
    def perform_mutation(cls, _root, info, **data):
        post = cls.get_instance(info, **data)
        cls.delete_assigned_attribute_values(post)
        response = super().perform_mutation(_root, info, **data)
        transaction.on_commit(lambda: info.context.plugins.post_deleted(post))
        return response


class PostTypeCreateInput(graphene.InputObjectType):
    name = graphene.String(description="Name of the post type.")
    slug = graphene.String(description="Post type slug.")


class PostTypeCreate(ModelMutation):
    class Arguments:
        input = PostTypeCreateInput(
            description="Fields required to create post type.", required=True
        )

    class Meta:
        description = "Create a new post type."
        model = models.PostType
        object_type = PostType
        permissions = (PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def clean_input(cls, info, instance, data):
        cleaned_input = super().clean_input(info, instance, data)
        errors = defaultdict(list)
        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "name", cleaned_input
            )
        except ValidationError as error:
            error.code = PostErrorCode.REQUIRED.value
            errors["slug"].append(error)

        cls.validate_attributes(
            errors, cleaned_input.get("add_attributes"), "add_attributes"
        )

        if errors:
            raise ValidationError(errors)

        return cleaned_input

    @classmethod
    def _save_m2m(cls, info, instance, cleaned_data):
        super()._save_m2m(info, instance, cleaned_data)
        attributes = cleaned_data.get("add_attributes")
        if attributes is not None:
            instance.post_attributes.add(*attributes)

    @classmethod
    def post_save_action(cls, info, instance, cleaned_input):
        info.context.plugins.post_type_created(instance)


class PostTypeUpdate(ModelMutation):
    class Arguments:
        id = graphene.ID(description="ID of the post type to update.")
        input = PostTypeCreateInput(
            description="Fields required to update post type.", required=True
        )

    class Meta:
        description = "Update post type."
        model = models.PostType
        object_type = PostType
        permissions = (PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def clean_input(cls, info, instance, data):
        errors = defaultdict(list)
        error = check_for_duplicates(data)
        if error:
            error.code = PostErrorCode.DUPLICATED_INPUT_ITEM.value
            errors["attributes"].append(error)

        cleaned_input = super().clean_input(info, instance, data)
        try:
            cleaned_input = validate_slug_and_generate_if_needed(
                instance, "name", cleaned_input
            )
        except ValidationError as error:
            error.code = PostErrorCode.REQUIRED
            errors["slug"].append(error)

        if errors:
            raise ValidationError(errors)

        return cleaned_input

    @classmethod
    def _save_m2m(cls, info, instance, cleaned_data):
        super()._save_m2m(info, instance, cleaned_data)        

    @classmethod
    def post_save_action(cls, info, instance, cleaned_input):
        info.context.plugins.post_type_updated(instance)


class PostTypeDelete(ModelDeleteMutation):
    class Arguments:
        id = graphene.ID(required=True, description="ID of the post type to delete.")

    class Meta:
        description = "Delete a post type."
        model = models.PostType
        object_type = PostType
        permissions = (PostTypePermissions.MANAGE_POST_TYPES_AND_ATTRIBUTES,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    @traced_atomic_transaction()
    def perform_mutation(cls, _root, info, **data):
        return super().perform_mutation(_root, info, **data)


    @classmethod
    def post_save_action(cls, info, instance, cleaned_input):
        transaction.on_commit(lambda: info.context.plugins.post_type_deleted(instance))


class PostMediaCreateInput(graphene.InputObjectType):
    alt = graphene.String(description="Alt text for a post media.")
    image = Upload(
        required=False, description="Represents an image file in a multipart request."
    )
    post = graphene.ID(
        required=True, description="ID of an post.", name="post"
    )
    media_url = graphene.String(
        required=False, description="Represents an URL to an external media."
    )


class PostMediaCreate(BaseMutation):
    post = graphene.Field(Post)
    media = graphene.Field(PostMedia)

    class Arguments:
        input = PostMediaCreateInput(
            required=True, description="Fields required to create a post media."
        )

    class Meta:
        description = (
            "Create a media object (image or video URL) associated with post. "
            "For image, this mutation must be sent as a `multipart` request. "
            "More detailed specs of the upload format can be found here: "
            "https://github.com/jaydenseric/graphql-multipart-request-spec"
        )
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def validate_input(cls, data):
        image = data.get("image")
        media_url = data.get("media_url")

        if not image and not media_url:
            raise ValidationError(
                {
                    "input": ValidationError(
                        "Image or external URL is required.",
                        code=PostErrorCode.REQUIRED,
                    )
                }
            )
        if image and media_url:
            raise ValidationError(
                {
                    "input": ValidationError(
                        "Either image or external URL is required.",
                        code=PostErrorCode.DUPLICATED_INPUT_ITEM,
                    )
                }
            )

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        data = data.get("input")
        cls.validate_input(data)
        post = cls.get_node_or_error(
            info,
            data["post"],
            field="post",
            only_type=Post,
            qs=models.Post.objects.prefetched_for_webhook(),
        )

        alt = data.get("alt", "")
        image = data.get("image")
        media_url = data.get("media_url")
        if image:
            image_data = info.context.FILES.get(image)
            validate_image_file(image_data, "image", PostErrorCode)
            add_hash_to_file_name(image_data)
            media = post.media.create(
                image=image_data, alt=alt, type=PostMediaTypes.IMAGE
            )
        if media_url:
            # Remote URLs can point to the images or oembed data.
            # In case of images, file is downloaded. Otherwise we keep only
            # URL to remote media.
            if is_image_url(media_url):
                validate_image_url(media_url, "media_url", PostErrorCode.INVALID)
                filename = get_filename_from_url(media_url)
                image_data = requests.get(media_url, stream=True)
                image_file = File(image_data.raw, filename)
                media = post.media.create(
                    image=image_file,
                    alt=alt,
                    type=PostMediaTypes.IMAGE,
                )
            else:
                oembed_data, media_type = get_oembed_data(media_url, "media_url")
                media = post.media.create(
                    external_url=oembed_data["url"],
                    alt=oembed_data.get("title", alt),
                    type=media_type,
                    oembed_data=oembed_data,
                )

        info.context.plugins.post_updated(post)
        return PostMediaCreate(post=post, media=media)


class PostMediaUpdateInput(graphene.InputObjectType):
    alt = graphene.String(description="Alt text for a post media.")


class PostMediaUpdate(BaseMutation):
    post = graphene.Field(Post)
    media = graphene.Field(PostMedia)

    class Arguments:
        id = graphene.ID(required=True, description="ID of a post media to update.")
        input = PostMediaUpdateInput(
            required=True, description="Fields required to update a post media."
        )

    class Meta:
        description = "Updates a post media."
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        media = cls.get_node_or_error(info, data.get("id"), only_type=PostMedia)
        post = models.Post.objects.prefetched_for_webhook().get(
            pk=media.post_id
        )
        alt = data.get("input").get("alt")
        if alt is not None:
            media.alt = alt
            media.save(update_fields=["alt"])
        info.context.plugins.post_updated(post)
        return PostMediaUpdate(post=post, media=media)


class PostMediaReorder(BaseMutation):
    post = graphene.Field(Post)
    media = NonNullList(PostMedia)

    class Arguments:
        post_id = graphene.ID(
            required=True,
            description="ID of post that media order will be altered.",
        )
        media_ids = NonNullList(
            graphene.ID,
            required=True,
            description="IDs of a post media in the desired order.",
        )

    class Meta:
        description = "Changes ordering of the post media."
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def perform_mutation(cls, _root, info, post_id, media_ids):
        post = cls.get_node_or_error(
            info,
            post_id,
            field="post_id",
            only_type=Post,
            qs=models.Post.objects.prefetched_for_webhook(),
        )

        # we do not care about media with the to_remove flag set to True
        # as they will be deleted soon
        if len(media_ids) != post.media.exclude(to_remove=True).count():
            raise ValidationError(
                {
                    "order": ValidationError(
                        "Incorrect number of media IDs provided.",
                        code=PostErrorCode.INVALID,
                    )
                }
            )

        ordered_media = []
        for media_id in media_ids:
            media = cls.get_node_or_error(
                info, media_id, field="order", only_type=PostMedia
            )
            if media and media.post != post:
                raise ValidationError(
                    {
                        "order": ValidationError(
                            "Media %(media_id)s does not belong to this post.",
                            code=PostErrorCode.NOT_POSTS_IMAGE,
                            params={"media_id": media_id},
                        )
                    }
                )
            ordered_media.append(media)

        update_ordered_media(ordered_media)

        info.context.plugins.post_updated(post)
        return PostMediaReorder(post=post, media=ordered_media)


class PostMediaDelete(BaseMutation):
    post = graphene.Field(Post)
    media = graphene.Field(PostMedia)

    class Arguments:
        id = graphene.ID(required=True, description="ID of a post media to delete.")

    class Meta:
        description = "Deletes a post media."
        permissions = (PostPermissions.MANAGE_POSTS,)
        error_type_class = PostError
        error_type_field = "post_errors"

    @classmethod
    def perform_mutation(cls, _root, info, **data):
        media_obj = cls.get_node_or_error(info, data.get("id"), only_type=PostMedia)
        if media_obj.to_remove:
            raise ValidationError(
                {
                    "media_id": ValidationError(
                        "Media not found.",
                        code=PostErrorCode.NOT_FOUND,
                    )
                }
            )
        media_id = media_obj.id
        media_obj.set_to_remove()
        delete_post_media_task.delay(media_id)
        media_obj.id = media_id
        post = models.Post.objects.prefetched_for_webhook().get(
            pk=media_obj.post_id
        )
        info.context.plugins.post_updated(post)
        return PostMediaDelete(post=post, media=media_obj)
