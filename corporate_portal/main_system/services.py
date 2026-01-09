from django.db import transaction
from django.forms import ValidationError
from .models import Account, Company, Group, Individual


class CompanyService:
    """Service layer for company-related operations"""
    
    @staticmethod
    @transaction.atomic
    @staticmethod
    def validate_group_availability(group_ids, exclude_company_id=None):
        """
        Validate that groups are not already assigned to other companies.
        Returns a list of conflicts or None if all groups are available.
        """
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

    def create_company(username, password, company_data, group_ids, groups_lookup):
        """
        Create a new company with account and groups
        
        Args:
            username: Account username
            password: Account password
            company_data: Dict with company fields (company_name, nepali_name, etc.)
            group_ids: List of group IDs to assign
            groups_lookup: Dict mapping group_id to group_name
        
        Returns:
            Company instance
        """

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
        # Create account
        account = Account.objects.create(
            username=username,
            password=password,
            type='company'
        )
        
        # Create company
        company = Company.objects.create(
            username=account,
            **company_data
        )
        
        # Create groups
        for gid in group_ids:
            group_name = groups_lookup.get(gid, '')
            Group.objects.create(
                company_id=company,
                group_id=gid,
                group_name=group_name,
                isactive=True
            )
        
        return company
    
    @staticmethod
    @transaction.atomic
    def update_company(company, username=None, password=None, company_data=None, 
                    group_ids=None, groups_lookup=None):
        """
        Update existing company, optionally updating account and groups
        
        Args:
            company: Company instance to update
            username: New username (optional)
            password: New password (optional)
            company_data: Dict with company fields to update (optional)
            group_ids: List of group IDs (optional)
            groups_lookup: Dict mapping group_id to group_name (optional)
        
        Returns:
            Updated Company instance
        """
        account = company.username
        
        # Validate groups (exclude current company's groups)
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
            account = Account.objects.create(
                username=username,
                password=old_account.password,
                type='company'
            )
            company.username = account
            old_account.delete()
        
        # Update password if provided
        if password:
            account.password = password
            account.save()
        
        # Update company fields
        if company_data:
            for field, value in company_data.items():
                setattr(company, field, value)
            company.save()
        
        # If company is inactive, mark all its groups as inactive
        if not company.isactive:
            Group.objects.filter(company_id=company).update(isactive=False)
        
        # Update groups if provided
        if group_ids is not None and groups_lookup is not None:
            # Mark all existing groups as deleted
            Group.objects.filter(company_id=company).update(isdeleted=True)
            
            # Create/reactivate selected groups
            for gid in group_ids:
                group_name = groups_lookup.get(gid, '')
                
                existing_group = Group.objects.filter(
                    company_id=company,
                    group_id=gid
                ).first()
                
                if existing_group:
                    existing_group.isdeleted = False
                    # Only set active if company is active
                    existing_group.isactive = company.isactive
                    existing_group.group_name = group_name
                    existing_group.save()
                else:
                    Group.objects.create(
                        company_id=company,
                        group_id=gid,
                        group_name=group_name,
                        # Use company's active status
                        isactive=company.isactive
                    )
        
        return company
    
    @staticmethod
    @transaction.atomic
    def delete_company(company):
        """Delete company and its account"""
        account = company.username
        company.delete()
        account.delete()


class IndividualService:
    """Service layer for individual-related operations"""
    
    @staticmethod
    @transaction.atomic
    def create_individual(username, password, individual_data):
        """
        Create a new individual with account
        
        Args:
            username: Account username
            password: Account password
            individual_data: Dict with individual fields (group_id, user_full_name)
        
        Returns:
            Individual instance
        """
        # Create account
        account = Account.objects.create(
            username=username,
            password=password,
            type='individual'
        )
        
        # Create individual
        individual = Individual.objects.create(
            username=account,
            **individual_data
        )
        
        return individual
    
    @staticmethod
    @transaction.atomic
    def update_individual(individual, username=None, password=None, individual_data=None):
        """
        Update existing individual, optionally updating account
        
        Args:
            individual: Individual instance to update
            username: New username (optional)
            password: New password (optional)
            individual_data: Dict with individual fields to update (optional)
        
        Returns:
            Updated Individual instance
        """
        account = individual.username
        
        # Update username if provided and different
        if username and username != account.username:
            old_account = account
            account = Account.objects.create(
                username=username,
                password=old_account.password,
                type='individual'
            )
            individual.username = account
            old_account.delete()
        
        # Update password if provided
        if password:
            account.password = password
            account.save()
        
        # Update individual fields
        if individual_data:
            for field, value in individual_data.items():
                setattr(individual, field, value)
            individual.save()
        
        return individual
    
    @staticmethod
    @transaction.atomic
    def delete_individual(individual):
        """Delete individual and its account"""
        account = individual.username
        individual.delete()
        account.delete()