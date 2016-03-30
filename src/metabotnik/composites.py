from django.shortcuts import render
from metabotnik.models import Composite, Project
from django.http import HttpResponseNotFound
import requests
import traceback

def main(request):
    return render(request, 'composites.html', {'composites': Composite.objects.filter(user=request.user)})

def view(request, name):
    err = None
    r = requests.get('https://metabotnik.com/static/misc/%s' % name, verify=False)
    if r.status_code == 200:
        name_data = r.text
        projects = []
        for line in name_data.split('\n'):
            if not line.startswith('https://metabotnik.com/projects/'): continue
            try:
                p_pk = int(line[32:-1])
                p = Project.objects.get(pk=p_pk)
                if not p.public: continue
                projects.append(p)
            except:
                err = traceback.format_exc()
        return render(request, 'composite.html', 
                      {'name': name, 'projects': projects, 'err': err})
    return HttpResponseNotFound('Name [ %s ] could not be found' % name)