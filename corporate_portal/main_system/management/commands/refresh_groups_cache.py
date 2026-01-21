from django.core.management.base import BaseCommand #type: ignore
from main_system.utils import GroupAPIService

class Command(BaseCommand):
    help = 'Refresh the groups cache from the corporate API'

    def handle(self, *args, **options):
        self.stdout.write('Refreshing groups cache...')
        try:
            groups = GroupAPIService.refresh_cache()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully refreshed cache with {len(groups)} groups')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to refresh cache: {str(e)}')
            )