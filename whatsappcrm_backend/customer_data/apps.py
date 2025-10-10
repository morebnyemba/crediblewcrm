# whatsappcrm_backend/customer_data/apps.py

from django.apps import AppConfig

class CustomerDataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'customer_data'
    verbose_name = "Member & Family Data"

    def ready(self):
        """Import signals so they are connected when the app is ready."""
        import customer_data.signals  # noqa
