# services.py
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
        
        # Validate groups
        conflicts = CompanyService.validate_group_availability(group_ids)
        if conflicts:
            conflict_msgs = [
                f"{c['group_id']} ({c['group_name']}) - already assigned to {c['company_name']}"
                for c in conflicts
            ]
            raise ValidationError(
                f"The following groups are already assigned to other companies: {', '.join(conflict_msgs)}"
            )
        
        # Create account with hashed password
        account = Account.objects.create_user(
            username=username,
            password=password
        )
        
        # Add audit fields to account
        if user:
            account.created_by = user.username
            account.modified_by = user.username
            account.save()

        # Add audit fields
        if user:
            company_data['created_by'] = user.username
            company_data['modified_by'] = user.username
        
        # Create company
        company = Company.objects.create(
            username=account,
            **company_data
        )
        
        # Create groups with audit info
        for gid in group_ids:
            group_data = {
                'company_id': company,
                'group_id': gid,
                'group_name': groups_lookup.get(gid, ''),
                'isactive': company.isactive
            }
            if user:
                group_data['created_by'] = user.username
                group_data['modified_by'] = user.username
            
            Group.objects.create(**group_data)
        
        # Log company creation
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
        import json
        
        # ENFORCE permission check in service layer
        CompanyService.check_permission(user, 'main_system.change_company')
        
        account = company.username
        changes = {}
        
        # Validate groups
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
        
        # Update username if provided and different
        if username and username != account.username:
            old_username = account.username
            old_account = account
            account = Account.objects.create_user(
                username=username,
                password=old_account.password
            )
            account.password = old_account.password
            account.save()
            company.username = account
            old_account.delete()
            changes['username'] = {'old': old_username, 'new': username}
        
        # Update password if provided
        if password:
            account.set_password(password)
            account.save()
            changes['password'] = 'changed'
        
        # Track company data changes BEFORE adding modified_by
        if company_data:
            for field, new_value in company_data.items():
                # Skip audit fields
                if field in ['modified_by', 'created_by']:
                    continue
                
                old_value = getattr(company, field, None)
           
                # Handle boolean comparison properly
                if isinstance(old_value, bool) and isinstance(new_value, bool):
                    if old_value != new_value:
                        changes[field] = {'old': old_value, 'new': new_value}
                # Handle None values
                elif old_value is None and new_value is None:
                    continue
                elif old_value is None or new_value is None:
                    if old_value != new_value:
                        changes[field] = {'old': str(old_value) if old_value is not None else 'None', 
                                        'new': str(new_value) if new_value is not None else 'None'}
                # Regular comparison
                elif str(old_value).strip() != str(new_value).strip():
                    changes[field] = {'old': str(old_value), 'new': str(new_value)}
        
        # NOW add modified_by to company_data
        if company_data:
            if user:
                company_data['modified_by'] = user.username
            
            for field, value in company_data.items():
                setattr(company, field, value)
            company.save()
        
        # If company is inactive, mark all its groups as inactive
        if company_data and not company.isactive:
            Group.objects.filter(company_id=company).update(
                isactive=False,
                modified_by=user.username if user else None
            )
        
        # Track group changes
        if group_ids is not None and groups_lookup is not None:
            old_groups = list(Group.objects.filter(company_id=company, isdeleted=False).values_list('group_id', flat=True))
            
            Group.objects.filter(company_id=company).update(
                isdeleted=True,
                isactive=False,
                modified_by=user.username if user else None
            )
            
            for gid in group_ids:
                group_name = groups_lookup.get(gid, '')
                
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
        
        # Log update if there were changes
        if changes and user:
            AuditLog.create_log(
                action='update',
                target_username=company.username.username,
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
        
        # ENFORCE permission check in service layer
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
        # Soft delete account
        company.username.is_active = False
        company.username.modified_by = user.username if user else None
        company.username.save()
        
        # Audit log
        if user:
            AuditLog.create_log(
                action='soft_delete',
                target_username=company.username.username,
                target_type='company',
                performed_by=user.username,
                details=f"Company '{company.company_name}' soft deleted"
            )
        
        return company
    
    @staticmethod
    @transaction.atomic
    def hard_delete_company(company, user=None):
        """Hard delete company (Admin only)"""
        from .models import AuditLog
        import json
        
        # ENFORCE permission check in service layer - Admin only
        CompanyService.check_permission(user, 'main_system.delete_company')
        
        account = company.username
        company_name = company.company_name
        username = account.username
        
        # Log before deleting
        if user:
            AuditLog.create_log(
                action='hard_delete',
                target_username=username,
                target_type='company',
                performed_by=user.username,
                details=json.dumps({
                    'company_name': company_name,
                    'company_id': company.company_id
                })
            )
        
        company.delete()
        account.delete()
        
        return True
    
    @staticmethod
    @transaction.atomic
    def approve_company(company, user=None):
        """Approve company (Approver/Admin only)"""
        
        # ENFORCE permission check in service layer
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
        
        # Activate account
        company.username.is_active = True
        company.username.save()
        
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
        target_type = target_account.get_user_type()
        
        # Prevent self-modification through services
        if user.username == target_account.username:
            raise PermissionDenied("You cannot modify your own account through this service")
        
        # Editor cannot modify staff accounts
        if 'Editor' in user_groups and target_account.is_staff:
            raise PermissionDenied("Editors cannot modify staff accounts")
        
        # Admin cannot modify superusers
        if 'Admin' in user_groups and target_account.is_superuser:
            raise PermissionDenied("Admins cannot modify superuser accounts")
        
        return True
    
    @staticmethod
    @transaction.atomic
    def reset_password(account, new_password, user=None):
        """Reset account password with permission check and audit"""
        from .models import AuditLog
        
        # Check permissions
        AccountService.can_modify_account(user, account)
        
        # Set password
        account.set_password(new_password)
        account.modified_by = user.username if user else None
        account.save()
        
        # Audit log
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
        import json
        
        # ENFORCE permission check in service layer
        IndividualService.check_permission(user, 'main_system.add_individual')
        
        if not username or not password:
            raise ValidationError("Username and password are required")
        
        # Create account with hashed password
        account = Account.objects.create_user(
            username=username,
            password=password
        )
        
        # Add audit fields to account
        if user:
            account.created_by = user.username
            account.modified_by = user.username
            account.save()
        
        # Add audit fields
        if user:
            individual_data['created_by'] = user.username
            individual_data['modified_by'] = user.username
        
        # Create individual
        individual = Individual.objects.create(
            username=account,
            **individual_data
        )
        
        # Log individual creation
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
        import json
        
        # ENFORCE permission check in service layer
        IndividualService.check_permission(user, 'main_system.change_individual')
        
        account = individual.username
        changes = {}
        
        # Update username if provided and different
        if username and username != account.username:
            old_username = account.username
            old_account = account
            account = Account.objects.create_user(
                username=username,
                password=old_account.password
            )
            account.password = old_account.password
            account.save()
            individual.username = account
            old_account.delete()
            changes['username'] = {'old': old_username, 'new': username}
        
        # Update password if provided
        if password:
            account.set_password(password)
            account.save()
            changes['password'] = 'changed'
        
        # Track individual data changes
        old_data = {}
        if individual_data:
            for field, value in individual_data.items():
                old_value = getattr(individual, field, None)
                if str(old_value) != str(value):
                    old_data[field] = {'old': str(old_value), 'new': str(value)}
        
        # Update individual fields with audit info
        if individual_data:
            if user:
                individual_data['modified_by'] = user.username
            
            for field, value in individual_data.items():
                setattr(individual, field, value)
            individual.save()
        
        # Log update if there were changes
        if (changes or old_data) and user:
            changes.update(old_data)
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
        
        # ENFORCE permission check in service layer
        IndividualService.check_permission(user, 'main_system.soft_delete_individual')
        
        # Soft delete account
        individual.username.is_active = False
        individual.username.modified_by = user.username if user else None
        individual.username.save()
        
        # Update audit
        if user:
            individual.modified_by = user.username
            individual.save()
            
            # Audit log
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
        import json
        
        # ENFORCE permission check in service layer - Admin only
        IndividualService.check_permission(user, 'main_system.delete_individual')
        
        account = individual.username
        user_full_name = individual.user_full_name
        username = account.username
        
        # Log before deleting
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
        
        # ENFORCE permission check in service layer
        IndividualService.check_permission(user, 'main_system.approve_individual')
        
        # Activate account
        individual.username.is_active = True
        individual.username.save()
        
        # Update audit
        if user:
            individual.modified_by = user.username
            individual.save()
        
        return individual