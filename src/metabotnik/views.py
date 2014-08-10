from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotFound
from django.conf import settings
from dropbox.client import DropboxClient
from metabotnik.models import Project, new_task
import os

def home(request):
    return render(request, 'index.html')

def help(request, page):
    return render(request, 'help/%s.html' % page)

@login_required
def new_project(request):
    path = request.GET.get('new_with_folder')
    if not path:
        return render(request, 'projects.html',
                      {'message': 'No path specified for the new project?'})
    filecount = request.GET.get('filecount', 0)        
    project = Project.objects.create(path=path, user=request.user, num_files_on_dropbox=filecount)
    settings.STORAGE_PATH
    url = reverse('project', args=[project.pk])
    return redirect(url)

def projectpreview(request, project_id, hash, tipe):
    # Why the hash param?
    # It is basically ignored it can be any characters, but we are adding it to do cache-busting
    # othwerwise browsers would not display the /preview.jpg file again.
    # There is probably a better way to do this using some form of HTTP header, but yeah, TODO...
    project = Project.objects.get(pk=project_id)
    if project.file_path(tipe):
        return HttpResponse(open(project.file_path(tipe)), mimetype='image/jpg')
    return HttpResponseNotFound()

@require_POST
def generate(request, project_id):
    preview = True if request.POST.get('preview') else False
    t = new_task(request.user, {
                'action': 'generate',
                'preview': preview,
                'project_id': project_id
    })
    project = Project.objects.get(pk=project_id)
    project.layout = request.POST.get('layout', 'horizontal')
    project.status = 'generating'
    project.save()
    return HttpResponse(str(t.pk))

@login_required
def project(request, project_id):
    project = Project.objects.get(pk=project_id)
    return render(request, 'project.html', {'project':project})

@login_required
def projects(request):
    if request.GET.get('new_with_folder'):
        return new_project(request)
    return render(request, 'projects.html', 
                  {'projects':Project.objects.filter(user=request.user)})

@login_required
def folders(request):
    client = DropboxClient(request.user.dropboxinfo.access_token)
    path = request.GET.get('path', '/')
    folder_metadata = client.metadata(path)

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