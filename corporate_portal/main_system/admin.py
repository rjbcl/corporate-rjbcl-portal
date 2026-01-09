from django.contrib import admin
import json
import os
from django.conf import settings
from django_select2.forms import Select2MultipleWidget
from django import forms
from .models import Company, Group, Individual, Account

class CompanyAdminForm(forms.ModelForm):
    username = forms.CharField(
        max_length=100, 
        required=False,
        help_text="Leave blank to keep current username"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        required=False,
        help_text="Leave blank to keep current password"
    )
    group_ids = forms.MultipleChoiceField(
        required=False,
        widget=Select2MultipleWidget(attrs={
            'data-placeholder': 'Search and select groups...',
        }),
        help_text="Search and select groups for this company"
    )


    class Meta:
        model = Company
        fields = ['company_name', 'nepali_name', 'phone_number', 'telephone_number', 'email', 'isactive']
        exclude = ['username']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Load groups from JSON
        json_path = os.path.join(settings.BASE_DIR, 'main_system', 'data', 'groups.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            groups_data = json.load(f)
        
        # Create choices as (group_id, "group_id - group_name")
        choices = [(g['groupid'], f"{g['groupid']} - {g['groupname']}") for g in groups_data]
        self.fields['group_ids'].choices = choices
        
        # If editing existing company, pre-select existing groups
        if self.instance and self.instance.pk:
            existing_groups = Group.objects.filter(company_id=self.instance, isdeleted=False)
            selected = [g.group_id for g in existing_groups if g.group_id]
            self.fields['group_ids'].initial = selected
            self.fields['username'].initial = self.instance.username.username
            self.fields['username'].help_text = f"Current: {self.instance.username.username}. Leave blank to keep it."
        
        # Store groups data for later use
        self.groups_lookup = {g['groupid']: g['groupname'] for g in groups_data}

    def save(self, commit=True):
        company = super().save(commit=False)
        
        # Handle account creation or update
        if self.instance.pk:  # Editing existing company
            account = self.instance.username
            
            # Update username if provided
            new_username = self.cleaned_data.get('username', '').strip()
            if new_username and new_username != account.username:
                old_account = account
                account = Account.objects.create(
                    username=new_username,
                    password=old_account.password,
                    type='company'
                )
                company.username = account
                old_account.delete()
            
            # Update password if provided
            new_password = self.cleaned_data.get('password', '').strip()
            if new_password:
                account.password = new_password
                account.save()
                
        else:  # Creating new company
            new_username = self.cleaned_data.get('username', '').strip()
            new_password = self.cleaned_data.get('password', '').strip()
            
            if not new_username or not new_password:
                raise forms.ValidationError("Username and password are required for new companies")
            
            account = Account.objects.create(
                username=new_username,
                password=new_password,
                type='company'
            )
            company.username = account
        
        company.save()
            # Mark all existing groups as deleted
        Group.objects.filter(company_id=company).update(isdeleted=True)
            
            # Create/reactivate selected groups
        selected_group_ids = self.cleaned_data.get('group_ids', [])
            
        for gid in selected_group_ids:
            group_name = self.groups_lookup.get(gid, '')
                
                # Check if group already exists
            existing_group = Group.objects.filter(
                company_id=company, 
                group_id=gid
            ).first()
                
            if existing_group:
                    # Reactivate and update name
                existing_group.isdeleted = False
                existing_group.isactive = True
                existing_group.group_name = group_name
                existing_group.save()
            else:
                    # Create new group
                Group.objects.create(
                    company_id=company,
                    group_id=gid,
                    isactive=True
                )
        return company
    def clean_group_ids(self):
        selected_group_ids = self.cleaned_data.get('group_ids', [])
        
        if selected_group_ids:
            # Check if any selected group already belongs to another company
            existing_groups = Group.objects.filter(
                group_id__in=selected_group_ids,
                isdeleted=False
            )
            
            # If editing, exclude groups from current company
            if self.instance.pk:
                existing_groups = existing_groups.exclude(company_id=self.instance)
            
            if existing_groups.exists():
                # Get details of conflicting groups
                conflicts = []
                for group in existing_groups:
                    conflicts.append(
                        f"{group.group_id} ({group.group_name}) - already assigned to {group.company_id.company_name}"
                    )
                
                raise forms.ValidationError(
                    f"The following groups are already assigned to other companies: {', '.join(conflicts)}"
                )
        
        return selected_group_ids
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate for new companies
        if not self.instance.pk:
            if not cleaned_data.get('username'):
                raise forms.ValidationError("Username is required for new companies")
            if not cleaned_data.get('password'):
                raise forms.ValidationError("Password is required for new companies")
        
        return cleaned_data

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    form = CompanyAdminForm
    list_display = ("company_id", "username", "company_name", "isactive")
    list_filter = ("isactive",)
    
    class Media:
        css = {
            'all': ('https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',)
        }
        js = ('https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js',)
    
    def delete_model(self, request, obj):
        account = obj.username
        super().delete_model(request, obj)
        account.delete()
    
    def delete_queryset(self, request, queryset):
        accounts = [company.username for company in queryset]
        super().delete_queryset(request, queryset)
        for account in accounts:
            account.delete()


class IndividualAdminForm(forms.ModelForm):
    username = forms.CharField(
        max_length=100, 
        required=False,
        help_text="Leave blank to keep current username"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        required=False,
        help_text="Leave blank to keep current password"
    )

    class Meta:
        model = Individual
        fields = ['group_id', 'user_full_name']
        exclude = ['username']  # Add this line

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If editing existing individual, populate username
        if self.instance and self.instance.pk:
            self.fields['username'].initial = self.instance.username.username
            self.fields['username'].help_text = f"Current: {self.instance.username.username}. Leave blank to keep it."

    def save(self, commit=True):
        individual = super().save(commit=False)
        
        # Handle account creation or update
        if self.instance.pk:  # Editing existing individual
            account = self.instance.username
            
            # Update username if provided
            new_username = self.cleaned_data.get('username', '').strip()
            if new_username and new_username != account.username:
                old_account = account
                account = Account.objects.create(
                    username=new_username,
                    password=old_account.password,
                    type='individual'
                )
                individual.username = account
                old_account.delete()
            
            # Update password if provided
            new_password = self.cleaned_data.get('password', '').strip()
            if new_password:
                account.password = new_password
                account.save()
                
        else:  # Creating new individual
            new_username = self.cleaned_data.get('username', '').strip()
            new_password = self.cleaned_data.get('password', '').strip()
            
            if not new_username or not new_password:
                raise forms.ValidationError("Username and password are required for new individuals")
            
            account = Account.objects.create(
                username=new_username,
                password=new_password,
                type='individual'
            )
            individual.username = account
        
        individual.save()
        return individual

    def clean(self):
        cleaned_data = super().clean()
        
        # Validate for new individuals
        if not self.instance.pk:
            if not cleaned_data.get('username'):
                raise forms.ValidationError("Username is required for new individuals")
            if not cleaned_data.get('password'):
                raise forms.ValidationError("Password is required for new individuals")
        
        return cleaned_data

@admin.register(Individual)
class IndividualAdmin(admin.ModelAdmin):
    form = IndividualAdminForm
    list_display = ("user_id", "user_full_name", "username", "group_id","get_company_name")
    
    def get_company_name(self, obj):
        return obj.group_id.company_id.company_name if obj.group_id and obj.group_id.company_id and obj.group_id.company_id.company_name else "-"
    get_company_name.short_description = "Company Name"
    
    def delete_model(self, request, obj):
        account = obj.username
        super().delete_model(request, obj)
        account.delete()
    
    def delete_queryset(self, request, queryset):
        accounts = [individual.username for individual in queryset]
        super().delete_queryset(request, queryset)
        for account in accounts:
            account.delete()

