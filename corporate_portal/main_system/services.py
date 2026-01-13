# services.py
from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
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
        
        return company
    
    @staticmethod
    @transaction.atomic
    def update_company(company, username=None, password=None, company_data=None, group_ids=None, groups_lookup=None, user=None):
        """Update existing company with permission check"""
        
        # ENFORCE permission check in service layer
        CompanyService.check_permission(user, 'main_system.change_company')
        
        account = company.username
        
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
            old_account = account
            account = Account.objects.create_user(
                username=username,
                password=old_account.password
            )
            account.password = old_account.password
            account.save()
            company.username = account
            old_account.delete()
        
        # Update password if provided
        if password:
            account.set_password(password)
            account.save()
        
        # Update company fields
        if company_data:
            if user:
                company_data['modified_by'] = user.username
            
            for field, value in company_data.items():
                setattr(company, field, value)
            company.save()
        
        # If company is inactive, mark all its groups as inactive
        if not company.isactive:
            Group.objects.filter(company_id=company).update(
                isactive=False,
                modified_by=user.username if user else None
            )
        
        # Update groups if provided
        if group_ids is not None and groups_lookup is not None:
            Group.objects.filter(company_id=company).update(
                isdeleted=True,
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
        
        return company
    
    @staticmethod
    @transaction.atomic
    def soft_delete_company(company, user=None):
        """Soft delete company (set isactive=False)"""
        
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
        company.username.save()
        
        return company
    
    @staticmethod
    @transaction.atomic
    def hard_delete_company(company, user=None):
        """Hard delete company (Admin only)"""
        
        # ENFORCE permission check in service layer - Admin only

        
        CompanyService.check_permission(user, 'main_system.delete_company')
        
        account = company.username
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


class IndividualService(PermissionMixin):
    
    @staticmethod
    @transaction.atomic
    def create_individual(username, password, individual_data, user=None):
        """Create individual with permission check"""
        
        # ENFORCE permission check in service layer
        IndividualService.check_permission(user, 'main_system.add_individual')
        
        if not username or not password:
            raise ValidationError("Username and password are required")
        
        # Create account with hashed password
        account = Account.objects.create_user(
            username=username,
            password=password
        )
        # Add audit fields
        if user:
            individual_data['created_by'] = user.username
            individual_data['modified_by'] = user.username
        
        # Create individual
        individual = Individual.objects.create(
            username=account,
            **individual_data
        )
        
        return individual
    
    @staticmethod
    @transaction.atomic
    def update_individual(individual, username=None, password=None, individual_data=None, user=None):
        """Update individual with permission check"""
        
        # ENFORCE permission check in service layer
        IndividualService.check_permission(user, 'main_system.change_individual')
        
        account = individual.username
        
        # Update username if provided and different
        if username and username != account.username:
            old_account = account
            account = Account.objects.create_user(
                username=username,
                password=old_account.password
            )
            account.password = old_account.password
            account.save()
            individual.username = account
            old_account.delete()
        
        # Update password if provided
        if password:
            account.set_password(password)
            account.save()
        
        # Update individual fields with audit info
        if individual_data:
            if user:
                individual_data['modified_by'] = user.username
            
            for field, value in individual_data.items():
                setattr(individual, field, value)
            individual.save()
        
        return individual
    
    @staticmethod
    @transaction.atomic
    def soft_delete_individual(individual, user=None):
        """Soft delete individual"""
        
        # ENFORCE permission check in service layer
        IndividualService.check_permission(user, 'main_system.soft_delete_individual')
        
        # Soft delete account
        individual.username.is_active = False
        individual.username.save()
        
        # Update audit
        if user:
            individual.modified_by = user.username
            individual.save()
        
        return individual
    
    @staticmethod
    @transaction.atomic
    def hard_delete_individual(individual, user=None):
        """Hard delete individual (Admin only)"""
        
        # ENFORCE permission check in service layer - Admin only
        IndividualService.check_permission(user, 'main_system.delete_individual')
        
        account = individual.username
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