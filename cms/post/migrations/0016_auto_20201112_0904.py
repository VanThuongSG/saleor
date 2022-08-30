# Generated by Django 3.1 on 2020-11-12 09:04

from django.db import migrations

import cms.core.db.fields
import cms.core.utils.editorjs


class Migration(migrations.Migration):

    dependencies = [
        ("post", "0015_migrate_from_draftjs_to_editorjs_format"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="content_json",
            field=cms.core.db.fields.SanitizedJSONField(
                blank=True,
                default=dict,
                sanitizer=cms.core.utils.editorjs.clean_editor_js,
            ),
        ),
        migrations.AlterField(
            model_name="posttranslation",
            name="content_json",
            field=cms.core.db.fields.SanitizedJSONField(
                blank=True,
                default=dict,
                sanitizer=cms.core.utils.editorjs.clean_editor_js,
            ),
        ),
    ]
