from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.core.management import call_command


class PetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pets'
    
    def ready(self):
       post_migrate.connect(load_initial_data, sender=self)
       
def load_initial_data(sender, **kwargs):
    from django.db.utils import OperationalError
    try:
        call_command('loaddata', 'initial_data.json', app_label='pets')
    except OperationalError:
        pass