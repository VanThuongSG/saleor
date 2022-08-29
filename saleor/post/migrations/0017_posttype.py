import django.db.models.deletion
from django.db import migrations, models
from django.db.models.signals import post_migrate
from django.apps import apps as registry

import saleor.core.utils.json_serializer


def update_groups_with_manage_posts_with_new_permission(apps, schema_editor):
    def on_migrations_complete(sender=None, **kwargs):
        Group = apps.get_model("auth", "Group")
        Permission = apps.get_model("auth", "Permission")
        ContentType = apps.get_model("contenttypes", "ContentType")

        ct, _ = ContentType.objects.get_or_create(app_label="post", model="posttype")
        manage_post_types_and_attributes_perm, _ = Permission.objects.get_or_create(
            codename="manage_post_types_and_attributes",
            content_type=ct,
            name="Manage post types and attributes.",
        )

        groups = Group.objects.filter(
            permissions__content_type__app_label="post",
            permissions__codename="manage_posts",
        )
        for group in groups:
            group.permissions.add(manage_post_types_and_attributes_perm)

    sender = registry.get_app_config("post")
    post_migrate.connect(on_migrations_complete, weak=False, sender=sender)


def add_post_types_to_existing_posts(apps, schema_editor):
    Post = apps.get_model("post", "Post")
    PostType = apps.get_model("post", "PostType")

    posts = Post.objects.all()

    if posts:
        post_type = PostType.objects.create(name="Default", slug="default")

        post_type.posts.add(*posts)


class Migration(migrations.Migration):

    dependencies = [
        ("post", "0016_auto_20201112_0904"),
    ]

    operations = [
        migrations.CreateModel(
            name="PostType",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "private_metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=saleor.core.utils.json_serializer.CustomJsonEncoder,
                        null=True,
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=saleor.core.utils.json_serializer.CustomJsonEncoder,
                        null=True,
                    ),
                ),
                ("name", models.CharField(max_length=250)),
                (
                    "slug",
                    models.SlugField(allow_unicode=True, max_length=255, unique=True),
                ),
            ],
            options={
                "ordering": ("slug",),
                "permissions": (
                    (
                        "manage_post_types_and_attributes",
                        "Manage post types and attributes.",
                    ),
                ),
            },
        ),
        migrations.RunPython(
            update_groups_with_manage_posts_with_new_permission,
            migrations.RunPython.noop,
        ),
        migrations.AddField(
            model_name="post",
            name="post_type",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="posts",
                to="post.posttype",
            ),
        ),
        migrations.RunPython(
            add_post_types_to_existing_posts, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name="post",
            name="post_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="posts",
                to="post.posttype",
            ),
        ),
    ]
