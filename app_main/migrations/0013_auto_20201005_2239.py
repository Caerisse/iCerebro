# Generated by Django 3.1 on 2020-10-05 22:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_main', '0012_auto_20201005_1253'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='botsettings',
            name='proxy_address',
        ),
        migrations.RemoveField(
            model_name='botsettings',
            name='proxy_port',
        ),
        migrations.AlterField(
            model_name='proxyaddress',
            name='last_used',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
