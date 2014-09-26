from django.core.management.base import BaseCommand
from metabotnik.models import Task
from metabotnik.tasks import execute_task

    
class Command(BaseCommand):
    help = "Run a specific task, specified by primary key on the command line"
    
    def handle(self, *args, **options):
        if len(args) < 1:
            raise Exception('You need to specify a Task pk as argument 1')
        task = Task.objects.get(pk=args[0])
        execute_task(task)