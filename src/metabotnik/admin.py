from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from metabotnik.models import DropBoxInfo, Project, File, Task

# Define an inline admin descriptor for Employee model
# which acts a bit like a singleton
class DropBoxInfoInline(admin.StackedInline):
    model = DropBoxInfo
    can_delete = False
    verbose_name_plural = 'DropBoxInfos'

# Define a new User admin
class UserAdmin(UserAdmin):
    inlines = (DropBoxInfoInline, )

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
admin.site.register(Task, TaskAdmin)