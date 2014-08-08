from django.shortcuts import render, resolve_url, redirect
from django.conf import settings
from dropbox.client import DropboxClient


def home(request):
    return render(request, 'index.html')

def folders(request):
    client = DropboxClient(request.user.dropboxinfo.access_token)
    path = request.GET.get('path', '/')
    folder_metadata = client.metadata(path)
    print folder_metadata

    # Given a path like: /a/b/c
    # We want the pathsplit to look like:
    # [('/', '/'), ('/a', 'a'), ('/a/b', 'b'), ('/a/b/c', 'c')]
    # So that we can easily build up a navtree in the template
    pathsplit = path.split('/')
    pathsplit = [('/'.join(pathsplit[:i+1]), x) for i,x in enumerate(pathsplit)]
    pathsplit = pathsplit[1:]

    # Count the number of JPEG files and their cumulative size
    jpeg_files = []
    filesize_total = 0

    # Maintain a list of folders so we can display the header to browse to them nicely
    folders = []

    for x in folder_metadata['contents']:
        if x['is_dir']:
            folders.append(x)
            continue
        if x['path'].lower().endswith('.jpg') and x['bytes'] > 0:
            filesize_total += x['bytes']
            jpeg_files.append(x)

    return render(request, 'folders.html', 
                  {'folder_metadata':folder_metadata, 
                   'folders': folders,
                   'path':path, 
                   'pathsplit': pathsplit,
                   'filesize_total': filesize_total, 
                   'jpeg_files': jpeg_files,
                  })