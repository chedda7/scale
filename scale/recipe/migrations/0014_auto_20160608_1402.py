# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipe', '0013_auto_20160331_1127'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='recipejobold',
            name='job',
        ),
        migrations.RemoveField(
            model_name='recipejobold',
            name='recipe',
        ),
        migrations.DeleteModel(
            name='recipejobold',
        ),
    ]
