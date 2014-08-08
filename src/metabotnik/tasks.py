from metabotnik.models import Project
from django.conf import settings
from dropbox.client import DropboxClient
import os
from PIL import Image

THUMBNAIL_SIZE = 128, 128

def download_dropboxfiles(payload):
    print 'Now downloading files for', repr(payload)
    
    # Get the Project
    project = Project.objects.get(pk=payload['project_id'])
    project.set_status('downloading')

    project_storage, originals_folder, thumbs_folder = project.storage_paths()
    for p in (project_storage, originals_folder, thumbs_folder):
        if not os.path.exists(p):
            os.mkdir(p)

    # Check to see what files to download from Dropbox
    client = DropboxClient(project.user.dropboxinfo.access_token)
    folder_metadata = client.metadata(project.path)
    for x in folder_metadata['contents']:
        if x['path'].lower().endswith('.jpg') and x['bytes'] > 0:
            # Download the file from Dropbox to local disk
            local_filename = os.path.split(x['path'].lower())[-1]
            local_filepath = os.path.join(originals_folder, local_filename)
            if os.path.exists(local_filepath): # and not payload.get('redownload') == True
                continue
            with client.get_file(x['path']) as f:
                open(local_filepath, 'wb').write(f.read())

            # And make the thumbnails
            img = Image.open(local_filepath)
            img.thumbnail(THUMBNAIL_SIZE, Image.ANTIALIAS)
            thumb_filepath = os.path.join(thumbs_folder, local_filename)
            img.save(thumb_filepath, "JPEG")
            img.close()

    project.set_status('layout')
