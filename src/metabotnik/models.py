from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import json
import traceback
import os

class DropBoxInfo(models.Model):
    user = models.OneToOneField(User, primary_key=True)
    access_token = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now=True)

project_status_choices = (
    ('new', 'New'),
    ('downloading', 'Busy Downloading Files'),
    ('layout', 'Needs Layout'),
    ('generating', 'Busy Generating'),
    ('done', 'Done'),
)
project_layout_choices = (
    ('horizontal', 'horizontal'),
    ('vertical', 'vertical')
)
class Project(models.Model):
    name = models.CharField(max_length=250, blank=True)
    path = models.TextField()
    user = models.ForeignKey(User, related_name='projects')
    status = models.CharField(max_length=100, choices=project_status_choices, default='new')
    num_files_on_dropbox = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    layout_mode = models.CharField(max_length=100, choices=project_layout_choices, default='horizontal')

    def __unicode__(self):
        return self.name if self.name else self.path

    def save(self, *args, **kwargs):
        super(Project, self).save(*args, **kwargs)
        # Famous last words: these payloads need more stucture, but let's not over-engineer yet...
        if self.status == 'new':
            new_task({
                'action': 'download_dropboxfiles',
                'project_id': self.pk
            })

    def set_status(self, status):
        self.status = status
        self.save()

    def storage_paths(self):
        project_storage = os.path.join(settings.STORAGE_PATH, 'project_%s' % self.pk)    
        originals_folder = os.path.join(project_storage, 'originals')
        thumbs_folder = os.path.join(project_storage, 'thumbs')
        return project_storage, originals_folder, thumbs_folder

    def num_files_local(self):
        _, originals_folder, _ = self.storage_paths()
        return len([f for f in os.listdir(originals_folder) if f.lower().endswith('.jpg')])


task_status_choices = (
    ('new', 'New'),
    ('wip', 'In Progress'),
    ('error', 'Error'),
    ('done', 'Done'),
)
class Task(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    timestamp = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=100, choices=task_status_choices, default='new')
    payload_data = models.TextField()

    def get_payload(self):
        try:
            return json.loads(self.payload_data)
        except (ValueError, TypeError):
            return {}
    def set_payload(self, payload):
        self.payload_data = json.dumps(payload)
        self.save()

    def execute(self):
        # import here to prevent circular references
        import metabotnik.tasks

        payload = self.get_payload()         
        action = payload.get('action')
        task_function = getattr(metabotnik.tasks, action)
        if task_function:
            self.status = 'wip'
            self.save()
            try:
                task_function(payload)
                self.status = 'done'
                self.save()
            except Exception:                
                payload['error'] = traceback.format_exc()
                self.status = 'error'
                self.set_payload(payload)        
        else:
            self.status = 'error'
            payload['error'] = 'Task %s is unrecognised' % action
            self.set_payload(payload)

def new_task(payload):
    'Where payload is a dict containing the task details'
    tmp = json.dumps(payload)    
    return Task.objects.create(payload_data=tmp)