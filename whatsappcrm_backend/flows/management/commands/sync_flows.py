# whatsappcrm_backend/flows/management/commands/sync_flows.py

import importlib
import pkgutil
from django.core.management.base import BaseCommand
from django.db import transaction
from flows.models import Flow, FlowStep, FlowTransition
from flows import definitions

class Command(BaseCommand):
    help = 'Syncs flow definitions from Python files into the database.'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("--- Starting flow synchronization ---"))

        all_flow_definitions = []
        # Discover all modules in the definitions package
        for _, name, _ in pkgutil.iter_modules(definitions.__path__):
            try:
                module = importlib.import_module(f'flows.definitions.{name}')
                if hasattr(module, 'flow_definition'):
                    all_flow_definitions.append(getattr(module, 'flow_definition'))
                    self.stdout.write(f"Found definition in: {name}.py")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Could not import or read from flows/definitions/{name}.py: {e}"))

        if not all_flow_definitions:
            self.stdout.write(self.style.WARNING("No flow definitions found in 'flows/definitions/' directory."))
            return

        for flow_def in all_flow_definitions:
            flow_name = flow_def['name']
            self.stdout.write(f"\n  Syncing flow: {flow_name}...")

            # Upsert Flow
            flow, created = Flow.objects.update_or_create(
                name=flow_name,
                defaults={
                    'friendly_name': flow_def.get('friendly_name', flow_name.replace('_', ' ').title()),
                    'description': flow_def.get('description', ''),
                    'trigger_keywords': flow_def.get('trigger_keywords', []),
                    'is_active': flow_def.get('is_active', True)
                }
            )
            self.stdout.write(self.style.SUCCESS(f"    {'Created' if created else 'Updated'} flow object."))

            # Sync steps
            defined_step_names = {step['name'] for step in flow_def['steps']}
            deleted_steps_count, _ = flow.steps.exclude(name__in=defined_step_names).delete()
            if deleted_steps_count > 0:
                self.stdout.write(self.style.WARNING(f"    Deleted {deleted_steps_count} orphaned steps."))

            step_objects = {}
            for step_def in flow_def['steps']:
                step_name = step_def['name']
                step, _ = FlowStep.objects.update_or_create(
                    flow=flow,
                    name=step_name,
                    defaults={
                        'step_type': step_def['step_type'],
                        'config': step_def.get('config', {}),
                        'is_entry_point': step_def.get('is_entry_point', False)
                    }
                )
                step_objects[step_name] = step

            # Sync transitions (delete and recreate is safest)
            for step_def in flow_def['steps']:
                current_step = step_objects[step_def['name']]
                current_step.outgoing_transitions.all().delete()
                for i, trans_def in enumerate(step_def.get('transitions', [])):
                    next_step = step_objects.get(trans_def['next_step_name'])
                    if next_step:
                        FlowTransition.objects.create(current_step=current_step, next_step=next_step, condition_config=trans_def.get('condition_config', {}), priority=trans_def.get('priority', i))
                    else:
                        self.stderr.write(self.style.ERROR(f"      ERROR: Next step '{trans_def['next_step_name']}' not found for step '{current_step.name}'. Skipping transition."))
            self.stdout.write(self.style.SUCCESS(f"  Successfully synced steps and transitions for: {flow_name}"))

        self.stdout.write(self.style.SUCCESS("\n--- Flow synchronization complete. ---"))