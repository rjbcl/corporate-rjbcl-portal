import json
import os
from django.contrib import admin
from django import forms
from django.conf import settings
from django_select2.forms import Select2MultipleWidget
from django.core.exceptions import ValidationError
from .models import Company, Group, Individual, Account
from .services import CompanyService, IndividualService


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
            'style': 'width: 100%;'
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
        
        # Create choices
        choices = [(g['groupid'], f"{g['groupname']} ({g['groupid']})") for g in groups_data]
        self.fields['group_ids'].choices = choices
        
        # Store groups lookup for later
        self.groups_lookup = {g['groupid']: g['groupname'] for g in groups_data}
        
        # If editing, pre-populate fields
        if self.instance and self.instance.pk:
            existing_groups = Group.objects.filter(company_id=self.instance, isdeleted=False)
            selected = [g.group_id for g in existing_groups if g.group_id]
            self.fields['group_ids'].initial = selected
            self.fields['username'].initial = self.instance.username.username
            self.fields['username'].help_text = f"Current: {self.instance.username.username}. Leave blank to keep it."

    def save(self, commit=True):
        username = self.cleaned_data.get('username', '').strip()
        password = self.cleaned_data.get('password', '').strip()
        group_ids = self.cleaned_data.get('group_ids', [])
        
        # Prepare company data
        company_data = {
            'company_name': self.cleaned_data.get('company_name'),
            'nepali_name': self.cleaned_data.get('nepali_name'),
            'phone_number': self.cleaned_data.get('phone_number'),
            'telephone_number': self.cleaned_data.get('telephone_number'),
            'email': self.cleaned_data.get('email'),
            'isactive': self.cleaned_data.get('isactive'),
        }
        
        try:
            if self.instance.pk:  # Update
                company = CompanyService.update_company(
                    company=self.instance,
                    username=username or None,
                    password=password or None,
                    company_data=company_data,
                    group_ids=group_ids,
                    groups_lookup=self.groups_lookup
                )
            else:  # Create
                company = CompanyService.create_company(
                    username=username,
                    password=password,
                    company_data=company_data,
                    group_ids=group_ids,
                    groups_lookup=self.groups_lookup
                )
        except ValidationError as e:
            # Re-raise validation errors so they display in the form
            self.add_error(None, e)
            raise
        
        return company

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username', '').strip()
        
        # Validate for new companies
        if not self.instance.pk:
            if not username:
                raise forms.ValidationError("Username is required for new companies")
            if not cleaned_data.get('password'):
                raise forms.ValidationError("Password is required for new companies")
            
            # Check if username already exists
            if Account.objects.filter(username=username).exists():
                self.add_error('username', "This username is already in use.")
        else:
            # For existing companies, check if new username conflicts
            if username:
                current_username = self.instance.username.username
                if username != current_username:
                    if Account.objects.filter(username=username).exists():
                        self.add_error('username', "This username is already in use.")
        
        return cleaned_data
    
    def clean_group_ids(self):
        selected_group_ids = self.cleaned_data.get('group_ids', [])
        
        if selected_group_ids:
            existing_groups = Group.objects.filter(
                group_id__in=selected_group_ids,
                isdeleted=False
            )
            
            if self.instance.pk:
                existing_groups = existing_groups.exclude(company_id=self.instance)
            
            if existing_groups.exists():
                conflicts = []
                for group in existing_groups:
                    conflicts.append(
                        f"{group.group_id} ({group.group_name}) - already assigned to {group.company_id.company_name}"
                    )
                
                raise forms.ValidationError(
                    f"The following groups are already assigned to other companies: {', '.join(conflicts)}"
                )
        
        return selected_group_ids
    def save_m2m(self):
        pass


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
        exclude = ['username']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.pk:
            self.fields['username'].initial = self.instance.username.username
            self.fields['username'].help_text = f"Current: {self.instance.username.username}. Leave blank to keep it."

    def save(self, commit=True):
        username = self.cleaned_data.get('username', '').strip()
        password = self.cleaned_data.get('password', '').strip()
        
        # Prepare individual data
        individual_data = {
            'group_id': self.cleaned_data.get('group_id'),
            'user_full_name': self.cleaned_data.get('user_full_name'),
        }
        
        if self.instance.pk:  # Update
            individual = IndividualService.update_individual(
                individual=self.instance,
                username=username or None,
                password=password or None,
                individual_data=individual_data
            )
        else:  # Create
            individual = IndividualService.create_individual(
                username=username,
                password=password,
                individual_data=individual_data
            )
        
        return individual

    def clean(self):
        cleaned_data = super().clean()
        
        if not self.instance.pk:
            if not cleaned_data.get('username'):
                raise forms.ValidationError("Username is required for new individuals")
            if not cleaned_data.get('password'):
                raise forms.ValidationError("Password is required for new individuals")
        
        return cleaned_data

    def save_m2m(self):
        pass


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    form = CompanyAdminForm
    list_display = ( "username", "company_name", "isactive")
    list_filter = ("isactive",)
    
    class Media:
        css = {
            'all': ('https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',)
        }
        js = ('https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js',)
    
    def delete_model(self, request, obj):
        CompanyService.delete_company(obj)
    
    def delete_queryset(self, request, queryset):
        for company in queryset:
            CompanyService.delete_company(company)


@admin.register(Individual)
class IndividualAdmin(admin.ModelAdmin):
    form = IndividualAdminForm
    list_display = ("user_id", "user_full_name", "username", "get_group_name", "group_id")
    
    def get_group_name(self, obj):
        if obj.group_id:
            if obj.group_id.group_name:
                return obj.group_id.group_name
            elif obj.group_id.group_id:
                return f"Group {obj.group_id.group_id}"
        return "-"
    get_group_name.short_description = "Group Name"
    
    def delete_model(self, request, obj):
        IndividualService.delete_individual(obj)
    
    def delete_queryset(self, request, queryset):
        for individual in queryset:
            IndividualService.delete_individual(individual)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("row_id", "group_id", "group_name", "company_id", "isactive", "isdeleted")
    list_filter = ("isactive", "isdeleted")


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("username", "type")
    list_filter = ("type",)