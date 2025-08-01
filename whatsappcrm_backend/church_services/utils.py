# whatsappcrm_backend/church_services/utils.py

from django.apps import apps
from django.forms.models import model_to_dict
import logging

logger = logging.getLogger(__name__)

def query_model_and_serialize(app_label, model_name, filters, order_by=None, limit=None):
    """
    Queries a Django model, serializes the results to a list of dictionaries,
    and handles potential errors.
    """
    try:
        Model = apps.get_model(app_label, model_name)
        queryset = Model.objects.filter(**filters)

        if order_by:
            queryset = queryset.order_by(*order_by)

        if limit is not None:
            queryset = queryset[:limit]

        results_list = [model_to_dict(obj) for obj in queryset]
        return results_list
    except LookupError:
        logger.error(f"Model '{app_label}.{model_name}' not found.")
        return None
    except Exception as e:
        logger.exception(f"Error querying model '{app_label}.{model_name}': {e}")
        return None


if __name__ == '__main__':
    # This is just an example of how the utils file can be tested
    print("This is a utilities file with helper functions for flows.")