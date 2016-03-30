from django.conf.urls import patterns, include, url
import metabotnik.views
import metabotnik.composites
import metabotnik.auth
from django.contrib import admin
admin.site.index_template = 'custom_admin_index.html'
admin.autodiscover()

urlpatterns = patterns('',    
    url(r'^$', metabotnik.views.home, name='home'),
    url(r'^help/(\w+)$', metabotnik.views.help, name='help'),

    url(r'^folders/$', metabotnik.views.folders, name='folders'),
    url(r'^projects/$', metabotnik.views.projects, name='projects'),    
    url(r'^projects/([0-9]+)/$', metabotnik.views.project, name='project'),
    url(r'^projects/([0-9]+)/edit$', metabotnik.views.edit_project, name='edit_project'),
    url(r'^projects/([0-9]+)/metadata$', metabotnik.views.metadata_project, name='metadata_project'),
    url(r'^projects/([0-9]+)/sorting$', metabotnik.views.sorting_project, name='sorting_project'),
    url(r'^projects/([0-9]+)/generate$', metabotnik.views.generate, name='generate'),
    url(r'^projects/([0-9]+)/delete$', metabotnik.views.delete_project, name='delete_project'),
    url(r'^projects/([0-9]+)/getdropbox$', metabotnik.views.getdropbox_project, name='getdropbox_project'),
    url(r'^projects/([0-9]+)/num_files_local$', metabotnik.views.num_files_local, name='num_files_local'),
    url(r'^projects/([0-9]+)/savesection$', metabotnik.views.savesection, name='savesection'),
    url(r'^projects/([0-9]+)/json$', metabotnik.views.json_project, name='json_project'),
    url(r'^composites/$', metabotnik.composites.main, name='composites'),
    url(r'^composites/([0-9A-Za-z]+)/$', metabotnik.composites.view, name='composite_view'),

    # Only to be used in development and only works if DEBUG is True
    url(r'^s/(.*)$', metabotnik.views.s),

    # Authentication
    url(r'^login$', metabotnik.auth.loginview, name='login'),
    url(r'^logout$', metabotnik.auth.logoutview, name='logout'),
    url(r'^dropboxauthredirect$', metabotnik.auth.dropboxauthredirect, name='dropboxauthredirect'),

    url(r'^admin/', admin.site.urls),
)
