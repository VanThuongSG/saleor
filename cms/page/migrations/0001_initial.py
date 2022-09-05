# Generated by Django 3.2.15 on 2022-08-31 08:20

import cms.core.db.fields
import cms.core.utils.editorjs
import cms.core.utils.json_serializer
import django.contrib.postgres.indexes
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Page',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('is_published', models.BooleanField(default=False)),
                ('private_metadata', models.JSONField(blank=True, default=dict, encoder=cms.core.utils.json_serializer.CustomJsonEncoder, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict, encoder=cms.core.utils.json_serializer.CustomJsonEncoder, null=True)),
                ('seo_title', models.CharField(blank=True, max_length=70, null=True, validators=[django.core.validators.MaxLengthValidator(70)])),
                ('seo_description', models.CharField(blank=True, max_length=300, null=True, validators=[django.core.validators.MaxLengthValidator(300)])),
                ('slug', models.SlugField(max_length=255, unique=True)),
                ('title', models.CharField(max_length=250)),
                ('content', cms.core.db.fields.SanitizedJSONField(blank=True, null=True, sanitizer=cms.core.utils.editorjs.clean_editor_js)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ('slug',),
                'permissions': (('manage_pages', 'Manage pages.'),),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PageTranslation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language_code', models.CharField(max_length=35)),
                ('seo_title', models.CharField(blank=True, max_length=70, null=True, validators=[django.core.validators.MaxLengthValidator(70)])),
                ('seo_description', models.CharField(blank=True, max_length=300, null=True, validators=[django.core.validators.MaxLengthValidator(300)])),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('content', cms.core.db.fields.SanitizedJSONField(blank=True, null=True, sanitizer=cms.core.utils.editorjs.clean_editor_js)),
            ],
            options={
                'ordering': ('language_code', 'page', 'pk'),
            },
        ),
        migrations.CreateModel(
            name='PageType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('private_metadata', models.JSONField(blank=True, default=dict, encoder=cms.core.utils.json_serializer.CustomJsonEncoder, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict, encoder=cms.core.utils.json_serializer.CustomJsonEncoder, null=True)),
                ('name', models.CharField(max_length=250)),
                ('slug', models.SlugField(allow_unicode=True, max_length=255, unique=True)),
            ],
            options={
                'ordering': ('slug',),
                'permissions': (('manage_page_types_and_attributes', 'Manage page types and attributes.'),),
                'abstract': False,
            },
        ),
        migrations.AddIndex(
            model_name='pagetype',
            index=django.contrib.postgres.indexes.GinIndex(fields=['private_metadata'], name='pagetype_p_meta_idx'),
        ),
        migrations.AddIndex(
            model_name='pagetype',
            index=django.contrib.postgres.indexes.GinIndex(fields=['metadata'], name='pagetype_meta_idx'),
        ),
        migrations.AddIndex(
            model_name='pagetype',
            index=django.contrib.postgres.indexes.GinIndex(fields=['name', 'slug'], name='page_pagety_name_7c1cb8_gin'),
        ),
        migrations.AddField(
            model_name='pagetranslation',
            name='page',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='page.page'),
        ),
        migrations.AddField(
            model_name='page',
            name='page_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pages', to='page.pagetype'),
        ),
        migrations.AlterUniqueTogether(
            name='pagetranslation',
            unique_together={('language_code', 'page')},
        ),
        migrations.AddIndex(
            model_name='page',
            index=django.contrib.postgres.indexes.GinIndex(fields=['private_metadata'], name='page_p_meta_idx'),
        ),
        migrations.AddIndex(
            model_name='page',
            index=django.contrib.postgres.indexes.GinIndex(fields=['metadata'], name='page_meta_idx'),
        ),
        migrations.AddIndex(
            model_name='page',
            index=django.contrib.postgres.indexes.GinIndex(fields=['title', 'slug'], name='page_page_title_964714_gin'),
        ),
    ]
