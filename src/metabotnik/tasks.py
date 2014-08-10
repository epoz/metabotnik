from metabotnik.models import Project
from dropbox.client import DropboxClient
import os
import traceback
from django.utils import timezone
import planodo

def execute_task(task):
    payload = task.get_payload()         
    action = payload.get('action')
    task_function = globals().get(action) # Consider doing a getattr(sys.modules[__name__], action) ?
    if task_function:
        task.status = 'wip'
        task.time_started = timezone.now()
        task.save()
        try:
            task_function(payload)
            task.status = 'done'
            task.time_ended = timezone.now()
            task.save()
        except Exception:                
            payload['error'] = traceback.format_exc()
            task.status = 'error'
            task.set_payload(payload)        
    else:
        task.status = 'error'
        payload['error'] = 'Task %s is unrecognised' % action
        task.set_payload(payload)

# Defined tasks follow here ############################################################

def make_preview(payload):
    project = Project.objects.get(pk=payload['project_id'])
    project.set_status('previewing')

    # Calculate a row_width, row_height based on layout, widest, sqrt numbr of files etc.
    row_width, row_height = 750, 270

    # Make all the originals the same height
    working = os.path.join(project.storage_path, 'wip')
    planodo.make_images_sameheight(project.originals_path, working, row_height)

    # Make the rows
    rows = os.path.join(project.storage_path, 'wip', 'rows')
    planodo.make_rows(working, rows,  row_width, row_height)

    # Make the final preview
    filename = os.path.join(project.storage_path, 'preview.jpg')
    previewfile = planodo.make_by_rows(rows, filename, row_width, row_height)
    project.preview_width, project.preview_height = previewfile.size
    project.status = 'layout'
    project.save()

def download_dropboxfiles(payload):
    print 'Now downloading files for', repr(payload)
    
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

    project.set_status('layout')
