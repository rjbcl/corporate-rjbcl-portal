# main_system/management/commands/setup_staff_roles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from main_system.models import Company, Group as CompanyGroup, Individual, Account


class Command(BaseCommand):
    help = 'Setup staff roles and permissions'

    def handle(self, *args, **kwargs):
        # Define staff roles and their permissions
        roles = {
            'Viewer': {
                'description': 'Read-only access to all data',
                'permissions': [
                    ('view_account', Account),
                    ('view_company', Company),
                    ('view_group', CompanyGroup),
                    ('view_individual', Individual),
                ]
            },
            'Editor': {
                'description': 'Can create, edit, and soft delete data',
                'permissions': [
                    ('view_account', Account),
                    ('add_account', Account),
                    ('change_account', Account),
                    ('view_company', Company),
                    ('add_company', Company),
                    ('change_company', Company),
                    ('soft_delete_company', Company),
                    ('view_group', CompanyGroup),
                    ('add_group', CompanyGroup),
                    ('change_group', CompanyGroup),
                    ('soft_delete_group', CompanyGroup),
                    ('view_individual', Individual),
                    ('add_individual', Individual),
                    ('change_individual', Individual),
                    ('soft_delete_individual', Individual),
                ]
            },
            'Approver': {
                'description': 'Can approve/reject records and soft delete',
                'permissions': [
                    ('view_account', Account),
                    ('view_company', Company),
                    ('approve_company', Company),
                    ('soft_delete_company', Company),
                    ('view_group', CompanyGroup),
                    ('approve_group', CompanyGroup),
                    ('soft_delete_group', CompanyGroup),
                    ('view_individual', Individual),
                    ('approve_individual', Individual),
                    ('soft_delete_individual', Individual),
                ]
            },
            'Admin': {
                'description': 'Full access including hard delete',
                'permissions': [
                    ('view_account', Account),
                    ('add_account', Account),
                    ('change_account', Account),
                    ('delete_account', Account),
                    ('view_company', Company),
                    ('add_company', Company),
                    ('change_company', Company),
                    ('delete_company', Company),
                    ('approve_company', Company),
                    ('soft_delete_company', Company),
                    ('view_group', CompanyGroup),
                    ('add_group', CompanyGroup),
                    ('change_group', CompanyGroup),
                    ('delete_group', CompanyGroup),
                    ('approve_group', CompanyGroup),
                    ('soft_delete_group', CompanyGroup),
                    ('view_individual', Individual),
                    ('add_individual', Individual),
                    ('change_individual', Individual),
                    ('delete_individual', Individual),
                    ('approve_individual', Individual),
                    ('soft_delete_individual', Individual),
                ]
            }
        }

        for role_name, role_data in roles.items():
            # Use get_or_create to prevent duplicates
            group, created = Group.objects.get_or_create(name=role_name)
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created group: {role_name}'))
            else:
                self.stdout.write(f'Group already exists: {role_name}')
            
            # Clear existing permissions
            group.permissions.clear()
            
            # Deduplicate permissions
            unique_permissions = []
            seen = set()
            
            for perm_codename, model in role_data['permissions']:
                perm_key = (perm_codename, model._meta.label)
                if perm_key not in seen:
                    unique_permissions.append((perm_codename, model))
                    seen.add(perm_key)
            
            # Add permissions
            for perm_codename, model in unique_permissions:
                content_type = ContentType.objects.get_for_model(model)
                try:
                    permission = Permission.objects.get(
                        codename=perm_codename,
                        content_type=content_type
                    )
                    group.permissions.add(permission)
                    self.stdout.write(f'  Added permission: {perm_codename}')
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'  Permission not found: {perm_codename}')
                    )
        
        self.stdout.write(self.style.SUCCESS('\nStaff roles setup complete!'))
        self.stdout.write('\nRole descriptions:')
        for role_name, role_data in roles.items():
            self.stdout.write(f'  {role_name}: {role_data["description"]}')