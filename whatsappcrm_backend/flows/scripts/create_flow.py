# whatsappcrm_backend/flows/scripts/create_flow.py
import importlib
import pkgutil
from django.db import transaction
from flows.models import Flow, FlowStep, FlowTransition
from flows import definitions as flow_definitions_package

def _create_or_update_flow_from_definition(flow_definition: dict):
    """Helper function to create or update a single flow from its new dictionary definition."""
    flow_name = flow_definition["name"]
    
    print(f'>>> Starting creation/update for flow: {flow_name}...')
    
    # Create or update the Flow object itself
    flow, created = Flow.objects.update_or_create(
        name=flow_name,
        defaults={
            "friendly_name": flow_definition.get("friendly_name", flow_name.replace("_", " ").title()),
            "description": flow_definition.get("description", ""),
            "trigger_keywords": flow_definition.get("trigger_keywords", []),
            "is_active": flow_definition.get("is_active", True)
        }
    )
    if created:
        print(f'>>> Flow "{flow_name}" was created.')
    else:
        print(f'>>> Flow "{flow_name}" was updated. Clearing old steps and transitions.')
        # Clear existing steps and transitions for a clean update
        flow.steps.all().delete()

    steps_map = {}
    initial_step_name = flow_definition.get("initial_step")

    if not initial_step_name:
        print(f'    ERROR: Flow definition for "{flow_name}" is missing the "initial_step" key. Skipping.')
        return

    # First pass: create all steps
    for step_name, step_data in flow_definition.get("steps", {}).items():
        try:
            step = FlowStep.objects.create(
                flow=flow,
                name=step_name,
                step_type=step_data["type"],
                is_entry_point=(step_name == initial_step_name),
                config=step_data.get("config", {})
            )
            steps_map[step_name] = step
            print(f'    Created step: {step.name}')
        except KeyError as e:
            print(f'    ERROR creating step "{step_name}" for "{flow_name}": Missing key {e}.')
            raise
        except Exception as e:
            print(f'    ERROR creating step "{step_name}" for "{flow_name}": {e}')
            raise

    # Second pass: create all transitions
    for step_name, step_data in flow_definition.get("steps", {}).items():
        current_step = steps_map.get(step_name)
        if not current_step:
            continue # Should not happen if first pass was successful

        for transition_key, next_step_name in step_data.get("transitions", {}).items():
            next_step = steps_map.get(next_step_name)
            if next_step:
                try:
                    # For this simple declarative format, we assume 'next' implies a default, always-true condition.
                    # The transition_key ('next') isn't stored in the model, but could be used for more complex logic if needed.
                    FlowTransition.objects.create(
                        current_step=current_step,
                        next_step=next_step,
                        condition_config={"type": "always_true"}, # Default condition for simple transitions
                        priority=0 # Default priority
                    )
                    print(f'        Created transition: {current_step.name} -> {next_step.name}')
                except Exception as e:
                    print(f'        ERROR creating transition from "{current_step.name}" to "{next_step_name}" for "{flow_name}": {e}')
                    raise
            else:
                # This handles transitions to steps that might not exist, e.g. a typo in the definition
                print(f'        WARNING: Could not create transition from "{current_step.name}". Target step "{next_step_name}" not found.')

    print(f'>>> {flow_name} steps and transitions processed.')


def run():
    """
    This script is executed by 'python manage.py runscript create_flow'.
    It automatically discovers and creates/updates all flows defined in the `flows.definitions` package.
    """
    print("Preparing to create/update flows from declarative definitions...")

    flow_definitions_to_process = []
    
    # Discover all modules within the `flows.definitions` package
    package_path = flow_definitions_package.__path__
    package_name = flow_definitions_package.__name__

    for _, module_name, _ in pkgutil.walk_packages(package_path, prefix=f"{package_name}."):
        try:
            module = importlib.import_module(module_name)
            # Find all uppercase dictionary variables in the module
            for attr_name in dir(module):
                if attr_name.isupper():
                    attr = getattr(module, attr_name)
                    if isinstance(attr, dict) and "name" in attr and "steps" in attr:
                        flow_definitions_to_process.append(attr)
                        print(f"Found flow definition: '{attr['name']}' in {module_name}")
        except Exception as e:
            print(f"Could not import or process module {module_name}: {e}")

    if not flow_definitions_to_process:
        print("No flow definitions found in `flows.definitions` package.")
        return

    with transaction.atomic():
        for flow_def in flow_definitions_to_process:
            try:
                _create_or_update_flow_from_definition(flow_def)
            except Exception as e:
                print(f">>> FATAL ERROR processing flow '{flow_def.get('name', 'Unknown')}': {e}")
                print(">>> Transaction will be rolled back.")
                # Re-raise to ensure the transaction is rolled back
                raise

    print(">>> Flow creation script finished successfully!")
