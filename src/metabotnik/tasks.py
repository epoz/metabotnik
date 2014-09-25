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

class RetryTaskException(Exception):
    'Raise this Exception in a task to have it retried later'
    pass

def execute_task(task):
    payload = task.get_payload()
    task_function = globals().get(task.action) # Consider doing a getattr(sys.modules[__name__], action) ?
    if task_function:

        # Bit of fun on local development machine
        if sys.platform == 'darwin':
            subprocess.call(['say', 'started task %s' % task.action])

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

def makethumbnails(payload):
    project = Project.objects.get(pk=payload['project_id'])

    output_filepath = os.path.join(project.storage_path, 'thumbnails')
    if not os.path.exists(output_filepath):
        os.mkdir(output_filepath)
    subprocess.call(['vipsthumbnail', '-o', '/%s.jpg'%output_filepath, '/%s.jpg'%project.originals_path])

def makedeepzoom(payload):
    project = Project.objects.get(pk=payload['project_id'])    
    project.set_status('dzgen')

    # Call VIPS to make the DZ
    input_filepath = os.path.join(project.storage_path, 'metabotnik.jpg')
    output_filepath = os.path.join(project.storage_path, 'deepzoom')

    # rm the deepzoom folder
    subprocess.call(['rm', '-rf', os.path.join(project.storage_path, 'deepzoom_files')])
    subprocess.call(['vips', 'dzsave', input_filepath, output_filepath, '--suffix', '.jpg'])

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
        ROW_HEIGHT = 200
        project.set_status('previewing')
    else:
        filename = os.path.join(project.storage_path, 'metabotnik.jpg')
        # When generating the actual metabotnik, make all the originals the same height as 
        # the first file found
        original_files = [x for x in os.listdir(project.originals_path) if x.endswith('.jpg')]
        if not original_files:
            return
        _, ROW_HEIGHT = Image.open( os.path.join(project.originals_path, original_files[0])).size
        ROW_HEIGHT = max(ROW_HEIGHT, 4000)
        project.set_status('generating')

    if os.path.exists(filename):
        os.remove(filename)


    # Make all the originals the same height
    working = os.path.join(project.storage_path, 'wip')
    planodo.make_images_sameheight(project.originals_path, working, ROW_HEIGHT)

    # Calculate a row_width, row_height based on layout, widest, sqrt numbr of files etc.
    row_width, row_height = planodo.calc_row_width_height(working)

    # Make the rows
    rows = os.path.join(project.storage_path, 'wip', 'rows')
    planodo.make_rows(working, rows,  row_width, row_height)

    # Make the final
    theimage = planodo.make_by_rows(rows, filename, row_width, row_height)
    if payload.get('preview'):
        project.preview_width, project.preview_height = theimage.size
    else:
        project.metabotnik_width, project.metabotnik_height = theimage.size        
        new_task(project.user, {
                'action': 'makedeepzoom',
                'project_id': project.pk
        })

    if payload.get('sendemail'):
        send_mail('Your generation task for project %s done' % project, 'It can be viewed at https://metabotnik.com/projects/%s/' % project.pk, 
                      'info@metabotnik.com', [project.user.email], fail_silently=False)

    project.set_status('layout')

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
    

    
    # Get the metadata as we are downloading the files,
    # but it can be run as a separate task too.
    extract_metadata(payload)

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
