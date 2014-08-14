from metabotnik.models import Project, new_task
from dropbox.client import DropboxClient
import os
import sys
import subprocess
import traceback
from django.utils import timezone
import planodo
from PIL import Image

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
            task_function(payload)
            task.status = 'done'
            task.time_ended = timezone.now()
            task.save()
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
    else:
        task.status = 'error'
        payload['error'] = 'Task %s is unrecognised' % task.action
        task.set_payload(payload)

# Defined tasks follow here ############################################################

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
    import pdb; pdb.set_trace()
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

    project.set_status('layout')

def download_dropboxfiles(payload):
    # Get the Project
    project = Project.objects.get(pk=payload['project_id'])
    project.set_status('downloading')

    # Check to see what files to download from Dropbox
    client = DropboxClient(project.user.dropboxinfo.access_token)
    folder_metadata = client.metadata(project.path)
    for x in folder_metadata['contents']:
        if x['path'].lower().endswith('.jpg') and x['bytes'] > 0:
            # Download the file from Dropbox to local disk
            local_filename = os.path.split(x['path'].lower())[-1]
            local_filepath = os.path.join(project.originals_path, local_filename)
            if os.path.exists(local_filepath): # and not payload.get('redownload') == True
                continue
            with client.get_file(x['path']) as f:
                open(local_filepath, 'wb').write(f.read())

    # Downloading files can take a long time
    # In the meantime this Project could have been changed by other tasks
    # Reload it before setting the status
    Project.objects.get(pk=payload['project_id']).set_status('layout')
