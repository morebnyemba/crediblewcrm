# whatsappcrm_backend/flows/apps.py

from django.apps import AppConfig

class FlowsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'flows'
    verbose_name = "Flows Management"
 
    def ready(self):
        # Import signals here to connect the receivers
        import flows.signals
        # Import tasks here to ensure they are discovered by Celery
        import flows.tasks
