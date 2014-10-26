from metabotnik.models import Project, File, new_task
from dropbox.client import DropboxClient
import os
import sys
import subprocess
import traceback
import json
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import planodo
from PIL import Image
from metabotnik.xmp import read_metadata
import random
import shutil

class RetryTaskException(Exception):
    'Raise this Exception in a task to have it retried later'
    pass

def execute_task(task):
    payload = task.get_payload()
    task_function = globals().get(task.action) # Consider doing a getattr(sys.modules[__name__], action) ?
    if task_function:

        # Bit of fun on local development machine
        if sys.platform == 'darwin':
            subprocess.call(['say', 'started task %s' % task.pk])

        task.status = 'wip'
        task.time_started = timezone.now()
        task.save()
        try:
            result = task_function(payload)
            if type(result) is dict:
                payload.update(result)
            # consider taking the return value from the task_function, if it is a dict
            # update the payload with the returned value
            task.status = 'done'
            task.time_ended = timezone.now()
            task.set_payload(payload)
            if sys.platform == 'darwin':
                subprocess.call(['say', 'task %s done' % task.pk])
        except RetryTaskException, e:
            payload['error'] = 'Retrying %s' % e
            task.status = 'new'
            task.set_payload(payload)
        except Exception:
            if sys.platform == 'darwin':
                subprocess.call(['say', 'error in task %s' % task.pk])

            payload['error'] = traceback.format_exc()
            task.status = 'error'
            task.set_payload(payload)
            # mail the error along
            send_mail('An error occurred in task %s ' % task.pk, 
                      '%s\nIt can be viewed at https://metabotnik.com/admin/metabotnik/task/%s/' % (payload['error'],task.pk), 
                      'info@metabotnik.com', 
                      [address for name, address in settings.ADMINS], 
                      fail_silently=True)

    else:
        task.status = 'error'
        payload['error'] = 'Task %s is unrecognised' % task.action
        task.set_payload(payload)

# Defined tasks follow here ############################################################

def layout(payload):
    project = Project.objects.get(pk=payload['project_id'])
    planodo.horzvert_layout(project)

def makethumbnails(payload):
    project = Project.objects.get(pk=payload['project_id'])

    output_filepath = os.path.join(project.storage_path, 'thumbnails')
    if not os.path.exists(output_filepath):
        os.mkdir(output_filepath)
    output_filepath += '/%s.jpg'

    # this command does not run in a shell, so we need to supply the wildcard arguments
    input_files = [os.path.join(project.originals_path, x) for x in os.listdir(project.originals_path) if x.lower().endswith('.jpg')]
    # Due to a file limit bug in vipsthumbnail, do 300 at a time : https://github.com/jcupitt/libvips/issues/182
    while input_files:
        subprocess.call(['%svipsthumbnail'%settings.VIPSBIN_PATH, '-o', output_filepath]+input_files[:300])
        input_files = input_files[300:]


def makedeepzoom(payload):
    project = Project.objects.get(pk=payload['project_id'])    
    project.set_status('dzgen')

    new_nonce = ''.join(random.choice('0123456789abcdef') for i in range(6))    
    # Call VIPS to make the DZ
    input_filepath = os.path.join(project.storage_path, 'metabotnik.jpg')
    output_filepath = os.path.join(project.storage_path, new_nonce)
    subprocess.call(['%svips'%settings.VIPSBIN_PATH, 'dzsave', input_filepath, output_filepath, '--suffix', '.jpg'])

    try:
        # clean up the previous deepzoom folder and dzi file
        old_path = os.path.join(project.storage_path, project.metabotnik_nonce+'_files')
        shutil.rmtree(old_path, ignore_errors=True)
        os.remove(os.path.join(project.storage_path, project.metabotnik_nonce+'.dzi'))
    except OSError:
        # maybe the files were removed by some other process, just move right along
        pass
        # though really, we need to do some better logging and signalling

    project.metabotnik_nonce = new_nonce
    project.set_status('done')


def generate(payload):
    project = Project.objects.get(pk=payload['project_id'])
    # Check to see if the number of files retrieved from Dropbox is done yet.
    # If not, just reset this task to new and return
    if project.num_files_local < project.num_files_on_dropbox:
        raise RetryTaskException('Local files < Dropbox files')


    if payload.get('preview'):
        filename = os.path.join(project.storage_path, 'preview.jpg')
        # For Previews, an arbitrary size
        # We need to add setting preview size to layouter...
        project.set_status('previewing')
    else:
        filename = os.path.join(project.storage_path, 'metabotnik.jpg')    
        project.set_status('generating')

    error_msgs = planodo.make_bitmap(project, filename)

    new_task(project.user, {
            'action': 'makedeepzoom',
            'project_id': project.pk
    })

    if payload.get('sendemail'):
        send_mail('Your generation task for project %s done' % project, 'It can be viewed at https://metabotnik.com/projects/%s/' % project.pk, 
                      'info@metabotnik.com', [project.user.email], fail_silently=False)

    project.set_status('layout')

    if error_msgs:
        return {'error': error_msgs}

def download_dropboxfiles(payload):
    # Get the Project
    project = Project.objects.get(pk=payload['project_id'])
    project.set_status('downloading')

    # Check to see what files to download from Dropbox
    client = DropboxClient(project.user.dropboxinfo.access_token)
    folder_metadata = client.metadata(project.path)
    num_files = 0
    for x in folder_metadata['contents']:
        if x['path'].lower().endswith('.jpg') and x['bytes'] > 0:
            # Download the file from Dropbox to local disk
            local_filename = os.path.split(x['path'].lower())[-1]
            local_filepath = os.path.join(project.originals_path, local_filename)
            num_files += 1
            if os.path.exists(local_filepath): # and not payload.get('redownload') == True
                continue
            with client.get_file(x['path']) as f:
                open(local_filepath, 'wb').write(f.read())
    

    
    # Get the metadata as a separate task
    new_task(project.user, {
        'action': 'extract_metadata',
        'project_id': project.pk
    })

    # schedule a thumbnail task
    new_task(project.user, {
        'action': 'makethumbnails',
        'project_id': project.pk
    })


    # Downloading files can take a long time
    # In the meantime this Project could have been changed by other tasks
    # Reload it before setting the status
    project = Project.objects.get(pk=payload['project_id'])
    project.num_files_on_dropbox = num_files
    project.status = 'layout'
    project.save()
    return {'downloaded_files_count':num_files}

def extract_metadata(payload):
    project = Project.objects.get(pk=payload['project_id'])
    current_files = {}
    for image in project.files.all():
        current_files[image.filename] = image
    #  For every file, read the metadata
    order = 1
    for filename in sorted(os.listdir(project.originals_path)):
        if not filename.endswith('.jpg'):
            continue
        filepath = os.path.join(project.originals_path, filename)
        image = current_files.get(filename, 
                    File(project=project, filename=filename, order=order)
        )
        order += 1
        tmp = read_metadata(filepath)
        image.metadata = json.dumps(tmp)
        # check the filesize
        image.size = os.stat(filepath).st_size
        # check the image size        
        image.width, image.height = Image.open(filepath).size
        image.save()

def makemetametabotnik(payload):
    'For all the public Projects with a metabotnik, make a thumbnail of them and combine into one giant metabotnik'
    metaproject = Project.objects.get(name='Metametabotnik')
    for p in Project.objects.filter(public=True):
        path = p.metabotnik_path()
        if not path: continue
        subprocess.call(['%svipsthumbnail'%settings.VIPSBIN_PATH, '-o', 'preview.jpg', '-s', '1000', path])
        preview_path = os.path.join(p.storage_path, 'preview.jpg')
        os.link(preview_path, os.path.join(metaproject.originals_path, 'project_%s.jpg' % p.pk))
    extract_metadata({'project_id':metaproject.pk})
