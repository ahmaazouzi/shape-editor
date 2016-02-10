# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shared', '0003_auto_20150928_0920'),
    ]

    operations = [
        migrations.RenameField(
            model_name='feature',
            old_name='geom_multipolygon',
            new_name='geom_multipolygon',
        ),
    ]
