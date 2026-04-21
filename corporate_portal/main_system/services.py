from django.db import transaction #type: ignore
from .models import AuditLog
import json
from django.core.exceptions import ValidationError, PermissionDenied #type: ignore
from .models import Company, Group, Account, Individual


class PermissionMixin:
    """Mixin for permission checking"""

    @staticmethod
    def check_permission(user, permission_string, raise_exception=True):
        """
        Check if user has permission
        permission_string: e.g., 'main_system.add_company'
        """
        if not user:
            if raise_exception:
                raise PermissionDenied("User authentication required")
            return False

        if user.is_superuser:
            return True

        has_perm = user.has_perm(permission_string)

        if not has_perm and raise_exception:
            raise PermissionDenied(f"You don't have permission: {permission_string}")

        return has_perm


class CompanyService(PermissionMixin):

    @staticmethod
    def validate_group_availability(group_ids, exclude_company_id=None):
        """Validate that groups are not already assigned to other companies"""
        if not group_ids:
            return None

        existing_groups = Group.objects.filter(
            group_id__in=group_ids,
            isdeleted=False
        )

        if exclude_company_id:
            existing_groups = existing_groups.exclude(company_id=exclude_company_id)

        if existing_groups.exists():
            conflicts = []
            for group in existing_groups:
                conflicts.append({
                    'group_id': group.group_id,
                    'group_name': group.group_name,
                    'company_name': group.company_id.company_name
                })
            return conflicts

        return None

    @staticmethod
    @transaction.atomic
    def create_company(username, password, company_data, group_ids, groups_lookup, user=None):
        """Create a new company with permission check"""
        from .models import AuditLog

        # ENFORCE permission check in service layer
        CompanyService.check_permission(user, 'main_system.add_company')

        if not username or not password:
            raise ValidationError("Username and password are required")

        # Validate groups — only block if a non-deleted group is already assigned elsewhere
        conflicts = CompanyService.validate_group_availability(group_ids)
        if conflicts:
            conflict_msgs = [
                f"{c['group_id']} ({c['group_name']}) - already assigned to {c['company_name']}"
                for c in conflicts
            ]
            raise ValidationError(
                f"The following groups are already assigned to other companies: {', '.join(conflict_msgs)}"
            )

        # Create the Account first (Company.username is a required FK to Account)
        account = Account.objects.create_user(
            username=username,
            password=password
        )
        if user:
            account.created_by = user.username
            account.modified_by = user.username
            account.save()

        # Link account to company_data and add audit fields
        company_data['username'] = account
        if user:
            company_data['created_by'] = user.username
            company_data['modified_by'] = user.username

        # Create company
        company = Company.objects.create(**company_data)

        # Create or resurrect groups
        for gid in group_ids:
            group_name = groups_lookup.get(gid, '')

            # Check if a soft-deleted record exists anywhere — resurrect it
            orphaned_group = Group.objects.filter(
                group_id=gid,
                isdeleted=True
            ).first()

            if orphaned_group:
                orphaned_group.company_id = company
                orphaned_group.isdeleted = False
                orphaned_group.isactive = company.isactive
                orphaned_group.group_name = group_name
                if user:
                    orphaned_group.modified_by = user.username
                orphaned_group.save()

            else:
                # Truly new group
                group_data = {
                    'company_id': company,
                    'group_id': gid,
                    'group_name': group_name,
                    'isactive': company.isactive
                }
                if user:
                    group_data['created_by'] = user.username
                    group_data['modified_by'] = user.username

                Group.objects.create(**group_data)

        # Audit log
        if user:
            AuditLog.create_log(
                action='create',
                target_username=account.username,
                target_type='company',
                performed_by=user.username,
                details=json.dumps({
                    'company_name': company.company_name,
                    'groups_assigned': list(group_ids)
                })
            )

        return company

    @staticmethod
    @transaction.atomic
    def update_company(company, username=None, password=None, company_data=None, group_ids=None, groups_lookup=None, user=None):
        """Update existing company with permission check"""
        from .models import AuditLog

        # ENFORCE permission check in service layer
        CompanyService.check_permission(user, 'main_system.change_company')

        changes = {}

        # Handle username change on the linked Account
        # Since username is the PK of Account, we must create a new Account and relink
        if username and username != company.username.username:
            if Account.objects.filter(username=username).exists():
                raise ValidationError("This username is already in use.")
            old_username = company.username.username
            old_account = company.username
            new_account = Account.objects.create_user(
                username=username,
                password=old_account.password  # carry over hashed password
            )
            # Assign the raw hash directly so create_user doesn't re-hash it
            new_account.password = old_account.password
            new_account.is_active = old_account.is_active
            new_account.is_staff = old_account.is_staff
            new_account.created_by = old_account.created_by
            new_account.modified_by = user.username if user else None
            new_account.save()
            company.username = new_account
            company.save()
            old_account.delete()
            changes['username'] = {'old': old_username, 'new': username}

        # Handle password change
        if password:
            account = company.username  # re-fetch after possible username change above
            account.set_password(password)
            if user:
                account.modified_by = user.username
            account.save()
            changes['password'] = 'changed'

        # Validate group availability (exclude current company's own groups)
        if group_ids is not None:
            conflicts = CompanyService.validate_group_availability(group_ids, exclude_company_id=company.company_id)
            if conflicts:
                conflict_msgs = [
                    f"{c['group_id']} ({c['group_name']}) - already assigned to {c['company_name']}"
                    for c in conflicts
                ]
                raise ValidationError(
                    f"The following groups are already assigned to other companies: {', '.join(conflict_msgs)}"
                )

        # Track company field changes BEFORE applying them
        if company_data:
            for field, new_value in company_data.items():
                if field in ['modified_by', 'created_by']:
                    continue

                old_value = getattr(company, field, None)

                if isinstance(old_value, bool) and isinstance(new_value, bool):
                    if old_value != new_value:
                        changes[field] = {'old': old_value, 'new': new_value}
                elif old_value is None and new_value is None:
                    continue
                elif old_value is None or new_value is None:
                    if old_value != new_value:
                        changes[field] = {
                            'old': str(old_value) if old_value is not None else 'None',
                            'new': str(new_value) if new_value is not None else 'None'
                        }
                elif str(old_value).strip() != str(new_value).strip():
                    changes[field] = {'old': str(old_value), 'new': str(new_value)}

        # Apply company_data updates
        if company_data:
            if user:
                company_data['modified_by'] = user.username

            for field, value in company_data.items():
                setattr(company, field, value)
            company.save()

        # If company set to inactive, cascade to its groups and linked account
        if company_data and not company.isactive:
            Group.objects.filter(company_id=company).update(
                isactive=False,
                modified_by=user.username if user else None
            )
            company.username.is_active = False
            company.username.save()

        # Handle group reassignment with orphan resurrection
        if group_ids is not None and groups_lookup is not None:
            old_groups = list(
                Group.objects.filter(company_id=company, isdeleted=False)
                .values_list('group_id', flat=True)
            )

            # Soft delete all current groups for this company first
            Group.objects.filter(company_id=company).update(
                isdeleted=True,
                isactive=False,
                modified_by=user.username if user else None
            )

            for gid in group_ids:
                group_name = groups_lookup.get(gid, '')

                # 1. Same company, just soft-deleted above — resurrect
                existing_group = Group.objects.filter(
                    company_id=company,
                    group_id=gid
                ).first()

                if existing_group:
                    existing_group.isdeleted = False
                    existing_group.isactive = company.isactive
                    existing_group.group_name = group_name
                    if user:
                        existing_group.modified_by = user.username
                    existing_group.save()

                else:
                    # 2. Soft-deleted under a different company — reassign and resurrect
                    orphaned_group = Group.objects.filter(
                        group_id=gid,
                        isdeleted=True
                    ).exclude(company_id=company).first()

                    if orphaned_group:
                        orphaned_group.company_id = company
                        orphaned_group.isdeleted = False
                        orphaned_group.isactive = company.isactive
                        orphaned_group.group_name = group_name
                        if user:
                            orphaned_group.modified_by = user.username
                        orphaned_group.save()

                    else:
                        # 3. Truly new group
                        group_data = {
                            'company_id': company,
                            'group_id': gid,
                            'group_name': group_name,
                            'isactive': company.isactive
                        }
                        if user:
                            group_data['created_by'] = user.username
                            group_data['modified_by'] = user.username

                        Group.objects.create(**group_data)

            new_groups = list(group_ids)
            if set(old_groups) != set(new_groups):
                changes['groups'] = {'old': old_groups, 'new': new_groups}

        # Audit log
        if changes and user:
            AuditLog.create_log(
                action='update',
                target_username=company.company_name,
                target_type='company',
                performed_by=user.username,
                details=json.dumps(changes)
            )

        return company

    @staticmethod
    @transaction.atomic
    def soft_delete_company(company, user=None):
        """Soft delete company (set isactive=False)"""
        from .models import AuditLog

        CompanyService.check_permission(user, 'main_system.soft_delete_company')

        company.isactive = False
        if user:
            company.modified_by = user.username
        company.save()

        # Cascade soft delete to groups
        Group.objects.filter(company_id=company).update(
            isactive=False,
            isdeleted=True,
            modified_by=user.username if user else None
        )

        if user:
            AuditLog.create_log(
                action='soft_delete',
                target_username=company.company_name,
                target_type='company',
                performed_by=user.username,
                details=f"Company '{company.company_name}' soft deleted"
            )

        return company

    @staticmethod
    @transaction.atomic
    def hard_delete_company(company, user=None):
        """Hard delete company and all linked accounts (Admin only)"""
        from .models import AuditLog

        CompanyService.check_permission(user, 'main_system.delete_company')

        company_name = company.company_name
        company_id = company.company_id
        account = company.username  # hold reference before deleting company

        if user:
            AuditLog.create_log(
                action='hard_delete',
                target_username=company_name,
                target_type='company',
                performed_by=user.username,
                details=json.dumps({
                    'company_name': company_name,
                    'company_id': company_id
                })
            )

        # Delete company (cascades to groups via FK on_delete=CASCADE)
        company.delete()
        # Delete the linked Account separately
        account.delete()

        return True

    @staticmethod
    @transaction.atomic
    def approve_company(company, user=None):
        """Approve company (Approver/Admin only)"""

        CompanyService.check_permission(user, 'main_system.approve_company')

        company.isactive = True
        if user:
            company.modified_by = user.username
        company.save()

        # Reactivate groups
        Group.objects.filter(company_id=company).update(
            isactive=True,
            isdeleted=False,
            modified_by=user.username if user else None
        )

        return company


class AccountService(PermissionMixin):

    @staticmethod
    def can_modify_account(user, target_account):
        """Check if user can modify target account"""
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required")

        if user.is_superuser:
            return True

        user_groups = list(user.groups.values_list('name', flat=True))

        if user.username == target_account.username:
            raise PermissionDenied("You cannot modify your own account through this service")

        if 'Editor' in user_groups and target_account.is_staff:
            raise PermissionDenied("Editors cannot modify staff accounts")

        if 'Admin' in user_groups and target_account.is_superuser:
            raise PermissionDenied("Admins cannot modify superuser accounts")

        return True

    @staticmethod
    @transaction.atomic
    def reset_password(account, new_password, user=None):
        """Reset account password with permission check and audit"""
        from .models import AuditLog

        AccountService.can_modify_account(user, account)

        account.set_password(new_password)
        account.modified_by = user.username if user else None
        account.save()

        if user:
            AuditLog.create_log(
                action='password_reset',
                target_username=account.username,
                target_type=account.get_user_type() or 'unknown',
                performed_by=user.username,
                details="Password reset via service",
                ip_address=None
            )

        return account


class IndividualService(PermissionMixin):

    @staticmethod
    @transaction.atomic
    def create_individual(username, password, individual_data, user=None):
        """Create individual with permission check"""
        from .models import AuditLog

        IndividualService.check_permission(user, 'main_system.add_individual')

        if not username or not password:
            raise ValidationError("Username and password are required")

        account = Account.objects.create_user(
            username=username,
            password=password
        )

        if user:
            account.created_by = user.username
            account.modified_by = user.username
            account.save()

        if user:
            individual_data['created_by'] = user.username
            individual_data['modified_by'] = user.username

        individual = Individual.objects.create(
            username=account,
            **individual_data
        )

        if user:
            AuditLog.create_log(
                action='create',
                target_username=account.username,
                target_type='individual',
                performed_by=user.username,
                details=json.dumps({
                    'user_full_name': individual.user_full_name,
                    'group_id': str(individual.group_id.group_id) if individual.group_id else None
                })
            )

        return individual

    @staticmethod
    @transaction.atomic
    def update_individual(individual, username=None, password=None, individual_data=None, user=None):
        """Update individual with permission check"""
        from .models import AuditLog

        IndividualService.check_permission(user, 'main_system.change_individual')

        account = individual.username
        changes = {}

        # Update username if provided and different
        # Since username is the PK of Account, create new and delete old
        if username and username != account.username:
            old_username = account.username
            old_account = account
            new_account = Account.objects.create_user(
                username=username,
                password=old_account.password
            )
            # Assign raw hash directly so it isn't re-hashed
            new_account.password = old_account.password
            new_account.is_active = old_account.is_active
            new_account.modified_by = user.username if user else None
            new_account.save()
            individual.username = new_account
            individual.save()
            old_account.delete()
            changes['username'] = {'old': old_username, 'new': username}
            account = new_account

        # Update password if provided
        if password:
            account.set_password(password)
            if user:
                account.modified_by = user.username
            account.save()
            changes['password'] = 'changed'

        # Track and apply individual field changes
        if individual_data:
            for field, value in individual_data.items():
                old_value = getattr(individual, field, None)
                if str(old_value) != str(value):
                    changes[field] = {'old': str(old_value), 'new': str(value)}

            if user:
                individual_data['modified_by'] = user.username

            for field, value in individual_data.items():
                setattr(individual, field, value)
            individual.save()

        if changes and user:
            AuditLog.create_log(
                action='update',
                target_username=individual.username.username,
                target_type='individual',
                performed_by=user.username,
                details=json.dumps(changes)
            )

        return individual

    @staticmethod
    @transaction.atomic
    def soft_delete_individual(individual, user=None):
        """Soft delete individual"""
        from .models import AuditLog

        IndividualService.check_permission(user, 'main_system.soft_delete_individual')

        individual.username.is_active = False
        individual.username.modified_by = user.username if user else None
        individual.username.save()

        if user:
            individual.modified_by = user.username
            individual.save()

            AuditLog.create_log(
                action='soft_delete',
                target_username=individual.username.username,
                target_type='individual',
                performed_by=user.username,
                details=f"Individual '{individual.user_full_name}' soft deleted"
            )

        return individual

    @staticmethod
    @transaction.atomic
    def hard_delete_individual(individual, user=None):
        """Hard delete individual (Admin only)"""
        from .models import AuditLog

        IndividualService.check_permission(user, 'main_system.delete_individual')

        account = individual.username
        user_full_name = individual.user_full_name
        username = account.username

        if user:
            AuditLog.create_log(
                action='hard_delete',
                target_username=username,
                target_type='individual',
                performed_by=user.username,
                details=json.dumps({
                    'user_full_name': user_full_name,
                    'user_id': individual.user_id
                })
            )

        individual.delete()
        account.delete()

        return True

    @staticmethod
    @transaction.atomic
    def approve_individual(individual, user=None):
        """Approve individual (Approver/Admin only)"""

        IndividualService.check_permission(user, 'main_system.approve_individual')

        individual.username.is_active = True
        individual.username.save()

        if user:
            individual.modified_by = user.username
            individual.save()

        return individual