from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from metabotnik.models import DropBoxInfo, Project, Task

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

class ProjectAdmin(admin.ModelAdmin):
    list_filter = ('status',)
admin.site.register(Project, ProjectAdmin)

class TaskAdmin(admin.ModelAdmin):
    list_display = ('action', 'status', 'user', 'created', 'time_ended')
    list_filter = ('status',)
admin.site.register(Task, TaskAdmin)