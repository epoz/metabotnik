from django.core.management.base import BaseCommand
from metabotnik.models import Task
from metabotnik.tasks import execute_task
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    
class Command(BaseCommand):
    help = "See if there are any tasks to be done and perform them"
    
    def handle(self, *args, **options):
        count = 0
        for task in Task.objects.filter(status='new'):
            execute_task(task)
            count += 1
        logging.debug('Executed %s tasks' % count) 