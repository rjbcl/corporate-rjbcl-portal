from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from main_system.models import (
    Account,
    Company,
    CompanyAccount,
    Group as CompanyGroup,
    UserVerification,
    AuditLog,
    ReportAccessLog,
)


class Command(BaseCommand):
    help = 'Setup staff roles and permissions'

    def handle(self, *args, **kwargs):

        # --------------------------------------------------------
        # Permission shorthand: (codename, Model)
        # Hard delete (delete_*) is intentionally excluded from all
        # roles — superuser only.
        # --------------------------------------------------------

        # Shared read-only base for all roles
        READ_ONLY_BASE = [
            ('view_own_account',      Account),
            ('view_account',          Account),
            ('view_company',          Company),
            ('view_companyaccount',   CompanyAccount),
            ('view_group',            CompanyGroup),
        ]

        # Editor extends read-only with write + soft-delete
        EDITOR_EXTRA = [
            ('add_company',                       Company),
            ('change_company',                    Company),
            ('soft_delete_company',               Company),
            ('add_companyaccount',                CompanyAccount),
            ('change_companyaccount',             CompanyAccount),
            ('soft_delete_company_account',       CompanyAccount),
            ('reset_company_account_password',    CompanyAccount),
            ('add_group',                         CompanyGroup),
            ('change_group',                      CompanyGroup),
            ('soft_delete_group',                 CompanyGroup),
        ]

        # Admin extends Editor with staff account management
        # and read access to audit/verification/report models
        ADMIN_EXTRA = [
            ('add_account',             Account),
            ('change_account',          Account),
            ('reset_staff_password',    Account),
            ('view_userverification',   UserVerification),
            ('view_auditlog',           AuditLog),
            ('view_reportaccesslog',    ReportAccessLog),
        ]

        roles = {
            'Viewer': {
                'description': (
                    'Read-only access to all company, group, and account data. '
                    'Cannot make any changes.'
                ),
                'permissions': READ_ONLY_BASE,
            },
            'Approver': {
                'description': (
                    'Same as Viewer for now. '
                    'Reserved for future approval workflows.'
                ),
                'permissions': READ_ONLY_BASE,
            },
            'Editor': {
                'description': (
                    'Can create, edit, and soft-delete companies, company accounts, '
                    'and groups. Can reset company account passwords. '
                    'Cannot manage staff accounts.'
                ),
                'permissions': READ_ONLY_BASE + EDITOR_EXTRA,
            },
            'Admin': {
                'description': (
                    'Full access except hard delete (superuser only). '
                    'Can manage staff accounts and view all audit/verification logs.'
                ),
                'permissions': READ_ONLY_BASE + EDITOR_EXTRA + ADMIN_EXTRA,
            },
        }

        for role_name, role_data in roles.items():
            group, created = Group.objects.get_or_create(name=role_name)

            if created:
                self.stdout.write(self.style.SUCCESS(f'Created group: {role_name}'))
            else:
                self.stdout.write(f'Group already exists: {role_name}')

            group.permissions.clear()

            # Deduplicate while preserving order
            seen = set()
            unique_permissions = []
            for perm_codename, model in role_data['permissions']:
                key = (perm_codename, model._meta.label)
                if key not in seen:
                    unique_permissions.append((perm_codename, model))
                    seen.add(key)

            for perm_codename, model in unique_permissions:
                content_type = ContentType.objects.get_for_model(model)
                try:
                    permission = Permission.objects.get(
                        codename=perm_codename,
                        content_type=content_type,
                    )
                    group.permissions.add(permission)
                    self.stdout.write(f'  Added: {perm_codename}')
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'  Permission not found: {perm_codename}')
                    )

        self.stdout.write(self.style.SUCCESS('\nStaff roles setup complete!'))
        self.stdout.write('\nRole descriptions:')
        for role_name, role_data in roles.items():
            self.stdout.write(f'  {role_name}: {role_data["description"]}')