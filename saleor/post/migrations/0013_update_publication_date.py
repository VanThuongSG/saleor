from datetime import date

from django.db import migrations


def set_missing_post_publication_date(apps, schema_editor):
    Post = apps.get_model("post", "Post")
    published_post = Post.objects.filter(
        publication_date__isnull=True, is_published=True
    )
    published_post.update(publication_date=date.today())


class Migration(migrations.Migration):
    dependencies = [
        ("post", "0012_auto_20200709_1102"),
    ]
    operations = [
        migrations.RunPython(set_missing_post_publication_date),
    ]
