from django.db import models
from django.dispatch.dispatcher import receiver
from django.contrib.auth.models import User
from django.conf import settings
from datetime import datetime
import json
import os
import shutil


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
    ('deleted', 'Deleted'),
)
project_layout_choices = (
    ('horizontal', 'horizontal'),
    ('vertical', 'vertical')
)
class Project(models.Model):
    name = models.CharField(max_length=250, blank=True)
    description = models.TextField(blank=True)
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
    public = models.BooleanField(default=False)

    def storage_size(self):
        'Returns the number of bytes of storage used by this project'
        total = 0
        for dirpath, dirnames, filenames in os.walk(self.storage_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                tmp = os.stat(filepath).st_size
                total += tmp
        return total

    def show(self):
        return self.name if self.name else self.path

    def __unicode__(self):
        return self.show()

    def save(self, *args, **kwargs):
        super(Project, self).save(*args, **kwargs)
        # Famous last words: these payloads need more stucture, but let's not over-engineer yet...
        if self.status == 'new':
            new_task(self.user, {
                'action': 'download_dropboxfiles',
                'project_id': self.pk
            })

    @property
    def user_full_name(self):
        return self.user.get_full_name()

    def set_file_order(self, file_list):
        # Given a list of file in file_list (which may contain blank lines too)
        # Try to set the order of the files of this project to match the file_list order
        if not file_list:
            return # just bail if empty
        current_files, incoming_files = {}, {}
        for f in self.files.all():
            current_files[f.filename] = f
            f.order = 0
            f.is_break = False
        for i, filename in enumerate(file_list):
            if filename:
                incoming_files[i] = filename
            else:
                # if there is a break, find the _preceding_ file and set a break flag on it
                break_filename_to_set = incoming_files[i-1]
                break_file = current_files.get(break_filename_to_set)
                if break_file:
                    break_file.is_break = True
            tmp_file = current_files.get(filename)
            if tmp_file:
                tmp_file.order = i

        for f in current_files.values():
            f.save()


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

    @property
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

    def deepzoom(self):
        tmp = os.path.join(self.storage_path, 'deepzoom_files')
        if os.path.exists(tmp):
            return tmp

@receiver(models.signals.post_delete, sender=Project)
def project_delete(sender, instance, **kwargs):
    shutil.rmtree(instance.storage_path, ignore_errors=True)

class File(models.Model):
    project = models.ForeignKey(Project, related_name='files')
    filename = models.CharField(max_length=250)
    metadata = models.TextField(null=True, blank=True) # store a JSON blob of data
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    size = models.IntegerField(default=0) # filesize in bytes
    order = models.IntegerField(default=0)
    is_break = models.BooleanField(default=False) # indicates that a column/row should be broken after this file

    class Meta:
        ordering = ('order',)

    def __unicode__(self):
        return u'%s : %s' % (self.project, self.filename)

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
    # scheduled time when this should not be run before
    # repeat count, default = 0
    # project foreign key

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

    def duration(self):
        # This should be a timedelta of the self.time_ended - self.time_started
        return self.created

    @property
    def user_full_name(self):
        return self.user.get_full_name()

def new_task(user, payload):
    'Where payload is a dict containing the task details'
    tmp = json.dumps(payload)
    action = payload.get('action')
    return Task.objects.create(action=action, payload_data=tmp, user=user)

# class Viewpoint(models.Model):
#     user = models.ForeignKey(User, related_name='tasks')
#     project = models.ForeignKey(Project, related_name='files')
# #    next = models.OneToOneField
