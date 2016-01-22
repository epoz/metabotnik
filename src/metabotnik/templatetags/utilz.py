from django import template
from metabotnik.models import project_status_choices

register = template.Library()

@register.filter
def nicestatus(dbval):
    'Converts a db status choice into a more user-friendly version'
    for val, stat in project_status_choices:
        if dbval == val:
            return stat
    return dbval

@register.simple_tag
def json_to_overlay(datadict):
    buf = []
    width, height = float(datadict['width']), float(datadict['height'])
    for i,obj in enumerate(datadict.get('images', [])):
        if 'LINK' in obj.get('metadata', {}):
            tmp = (obj['pk'], obj['x'], obj['y'])
            buf.append(u"{id: 'overlay%s', px:%s, py:%s}" % tmp)
    return u'\n,'.join(buf)
