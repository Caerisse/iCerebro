# Generated by Django 3.1 on 2020-08-13 18:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_main', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='botsettings',
            name='running',
            field=models.BooleanField(default=False),
        ),
    ]