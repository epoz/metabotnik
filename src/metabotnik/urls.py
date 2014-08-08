from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',    
    url(r'^$', 'metabotnik.views.home', name='home'),
    url(r'^folders$', 'metabotnik.views.folders', name='folders'),

    # Authentication
    url(r'^login$', 'metabotnik.auth.loginview', name='login'),
    url(r'^logout$', 'metabotnik.auth.logoutview', name='logout'),
    url(r'^dropboxauthredirect$', 'metabotnik.auth.dropboxauthredirect', name='dropboxauthredirect'),

    url(r'^admin/', include(admin.site.urls)),
)
