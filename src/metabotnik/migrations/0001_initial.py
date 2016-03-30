# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DropBoxInfo',
            fields=[
                ('user', models.OneToOneField(primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('access_token', models.CharField(max_length=100)),
                ('timestamp', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('filename', models.CharField(max_length=250)),
                ('metadata', models.TextField(null=True, blank=True)),
                ('width', models.IntegerField(default=0)),
                ('height', models.IntegerField(default=0)),
                ('x', models.IntegerField(default=0)),
                ('y', models.IntegerField(default=0)),
                ('new_width', models.IntegerField(default=0)),
                ('new_height', models.IntegerField(default=0)),
                ('size', models.IntegerField(default=0)),
                ('order', models.IntegerField(default=0)),
                ('is_break', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ('project', 'order'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=250, blank=True)),
                ('description', models.TextField(blank=True)),
                ('path', models.TextField()),
                ('status', models.CharField(default=b'new', max_length=100, choices=[(b'new', b'New'), (b'downloading', b'Busy Downloading Files'), (b'layout', b'Needs Layout'), (b'preview', b'Has a Preview'), (b'generating', b'Busy Generating'), (b'dzgen', b'Busy Making DeepZoom'), (b'done', b'Done with making your Metabotnik'), (b'deleted', b'Deleted')])),
                ('num_files_on_dropbox', models.IntegerField(default=0)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('layout_mode', models.CharField(default=b'horizontal', max_length=100, choices=[(b'horizontal', b'horizontal'), (b'vertical', b'vertical'), (b'random', b'random')])),
                ('layout_data', models.TextField(null=True, blank=True)),
                ('background_color', models.CharField(default=b'#ffffff', max_length=7)),
                ('metabotnik_nonce', models.CharField(max_length=100, null=True, blank=True)),
                ('public', models.BooleanField(default=False)),
                ('storage_size', models.IntegerField(default=0)),
                ('user', models.ForeignKey(related_name=b'projects', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('action', models.CharField(max_length=200)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('time_started', models.DateTimeField(null=True, blank=True)),
                ('time_ended', models.DateTimeField(null=True, blank=True)),
                ('status', models.CharField(default=b'new', max_length=100, choices=[(b'new', b'New'), (b'wip', b'In Progress'), (b'error', b'Error'), (b'done', b'Done')])),
                ('payload_data', models.TextField()),
                ('project', models.ForeignKey(related_name=b'tasks', blank=True, to='metabotnik.Project', null=True)),
                ('user', models.ForeignKey(related_name=b'tasks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('created',),
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='file',
            name='project',
            field=models.ForeignKey(related_name=b'files', to='metabotnik.Project'),
            preserve_default=True,
        ),
    ]
