# Generated by Django 3.2.6 on 2021-08-17 10:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("post", "0023_auto_20210526_0835"),
    ]

    operations = [
        migrations.AlterField(
            model_name="posttranslation",
            name="language_code",
            field=models.CharField(max_length=35),
        ),
    ]
