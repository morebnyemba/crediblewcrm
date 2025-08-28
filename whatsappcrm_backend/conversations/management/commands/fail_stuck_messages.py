# conversations/management/commands/fail_stuck_messages.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from conversations.models import Message

class Command(BaseCommand):
    """
    A Django management command to find messages that have been in the 'pending_dispatch'
    state for too long and mark them as 'failed'. This is useful for cleaning up
    tasks that may have gotten stuck in the queue due to a worker shutdown or other error.
    """
    help = 'Finds messages stuck in "pending_dispatch" for too long and marks them as "failed".'

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=5,
            help='The number of minutes a message must be in pending_dispatch to be considered stuck. Default is 5.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Show how many messages would be affected without actually changing them.",
        )

    def handle(self, *args, **options):
        minutes_threshold = options['minutes']
        is_dry_run = options['dry_run']
        
        stuck_threshold_time = timezone.now() - timedelta(minutes=minutes_threshold)

        self.stdout.write(f"Searching for 'pending_dispatch' messages created before {stuck_threshold_time.strftime('%Y-%m-%d %H:%M:%S')}...")

        stuck_messages_qs = Message.objects.filter(
            status='pending_dispatch',
            timestamp__lt=stuck_threshold_time
        )

        count = stuck_messages_qs.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No stuck messages found. Your queue is clean!"))
            return

        self.stdout.write(self.style.WARNING(f"Found {count} stuck message(s) to fail."))

        if is_dry_run:
            self.stdout.write(self.style.NOTICE("This is a dry run. No changes will be made."))
            return

        updated_count = stuck_messages_qs.update(
            status='failed',
            status_timestamp=timezone.now(),
            error_details={'error': f'Manually marked as failed by management command at {timezone.now().isoformat()}'}
        )

        self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} message(s) to 'failed' status."))

