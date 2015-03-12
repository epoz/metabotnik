from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings

from metabotnik.models import DropBoxInfo, Project, File, Task
from metabotnik.tasks import execute_task

# Define an inline admin descriptor for Employee model
# which acts a bit like a singleton
class DropBoxInfoInline(admin.StackedInline):
    model = DropBoxInfo
    can_delete = False
    verbose_name_plural = 'DropBoxInfos'

# Define a new User admin
class UserAdmin(UserAdmin):
    inlines = (DropBoxInfoInline, )
    actions = ['make_active'] 

    def make_active(self, request, queryset): 
        for user in queryset:
            user.is_active = True
            user.save()
            send_mail('Hooray! Your Metabotnik login has been activated', 
                      'Welcome %s,\nYou can now start making some gigantic zoomable images.\nHave fun at https://metabotnik.com/\nIf you have any questions or comments feel free to mail us at info@metabotnik.com' % user.get_full_name(), 
                      'info@metabotnik.com', 
                      [address for name, address in settings.ADMINS]+[user.email], 
                      fail_silently=True)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

class FileInline(admin.StackedInline):
    model = File

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('show', 'status', 'user_full_name', 'created')
    list_filter = ('status',)
#    inlines = (FileInline, )
    
admin.site.register(Project, ProjectAdmin)

class FileAdmin(admin.ModelAdmin):
    list_display = ('project', 'filename', 'pretty_size', 'width', 'height')
admin.site.register(File, FileAdmin)

class TaskAdmin(admin.ModelAdmin):
    list_display = ('project', 'action', 'status', 'user_full_name', 'created', 'time_ended', 'duration')
    list_filter = ('action', 'status',)
    date_hierarchy = 'created'
    actions = ['execute']

    def execute(self, request, queryset):
        for task in queryset:
            execute_task(task)

admin.site.register(Task, TaskAdmin)