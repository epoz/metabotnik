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
