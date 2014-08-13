from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import json
import os


class DropBoxInfo(models.Model):
    user = models.OneToOneField(User, primary_key=True)
    access_token = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now=True)

project_status_choices = (
    ('new', 'New'),
    ('downloading', 'Busy Downloading Files'),
    ('layout', 'Needs Layout'),
    ('preview', 'Has a Preview'),
    ('previewing', 'Busy Previewing'),
    ('generating', 'Busy Generating'),
    ('dzgen', 'Busy Making DeepZoom'),
    ('done', 'Done'),
)
project_layout_choices = (
    ('horizontal', 'horizontal'),
    ('vertical', 'vertical')
)
class Project(models.Model):
    name = models.CharField(max_length=250, blank=True)
    # Consider adding a 'source type' so that we can also get files from other places than Dropbox
    # For example, we might make one directly from Arkyves using symlinks,
    # and then path should point somewhere on local disk?
    path = models.TextField()
    user = models.ForeignKey(User, related_name='projects')
    status = models.CharField(max_length=100, choices=project_status_choices, default='new')
    num_files_on_dropbox = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    layout_mode = models.CharField(max_length=100, choices=project_layout_choices, default='horizontal')
    preview_width = models.IntegerField(default=0)
    preview_height = models.IntegerField(default=0)
    metabotnik_width = models.IntegerField(default=0)
    metabotnik_height = models.IntegerField(default=0)

    def __unicode__(self):
        return self.name if self.name else self.path

    def save(self, *args, **kwargs):
        super(Project, self).save(*args, **kwargs)
        # Famous last words: these payloads need more stucture, but let's not over-engineer yet...
        if self.status == 'new':
            new_task(self.user, {
                'action': 'download_dropboxfiles',
                'project_id': self.pk
            })

    def set_status(self, status):
        self.status = status
        self.save()

    @property
    def storage_path(self):
        tmp = os.path.join(settings.STORAGE_PATH, 'project_%s' % self.pk)
        if not os.path.exists(tmp): os.mkdir(tmp)
        return tmp

    @property
    def originals_path(self):
        tmp = os.path.join(self.storage_path, 'originals')
        if not os.path.exists(tmp): os.mkdir(tmp)
        return tmp

    def num_files_local(self):
        return len([f for f in os.listdir(self.originals_path) if f.lower().endswith('.jpg')])

    def file_path(self, tipe='preview'):
        tmp = os.path.join(self.storage_path, '%s.jpg' % tipe)
        if os.path.exists(tmp):
            return tmp
    # Following a bit of a weird construct, 
    # needed due to template not being able to call a method with an argument
    def file_path_metabotnik(self):
        return self.file_path(tipe='metabotnik')

task_status_choices = (
    ('new', 'New'),
    ('wip', 'In Progress'),
    ('error', 'Error'),
    ('done', 'Done'),
)
class Task(models.Model):
    action = models.CharField(max_length=200)
    user = models.ForeignKey(User, related_name='tasks')
    created = models.DateTimeField(auto_now_add=True)
    time_started = models.DateTimeField(null=True, blank=True)
    time_ended = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=100, choices=task_status_choices, default='new')
    payload_data = models.TextField()

    class Meta:
        ordering = ('created',)

    def get_payload(self):
        try:
            return json.loads(self.payload_data)
        except (ValueError, TypeError):
            return {}
    def set_payload(self, payload):
        self.payload_data = json.dumps(payload)
        self.save()

    def __unicode__(self):
        return u'%s %s' % (self.action, self.user.email)

def new_task(user, payload):
    'Where payload is a dict containing the task details'
    tmp = json.dumps(payload)
    action = payload.get('action')
    return Task.objects.create(action=action, payload_data=tmp, user=user)
