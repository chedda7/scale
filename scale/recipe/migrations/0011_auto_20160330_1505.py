# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipe', '0010_auto_20160330_1412'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='recipejob',
            new_name='recipejobold',
        ),
        migrations.AlterModelTable(
            name='recipejobold',
            table='recipe_job_old',
        ),
    ]
