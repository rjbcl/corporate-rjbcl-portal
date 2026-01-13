import json
import os
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib import admin
from django import forms
from django.conf import settings
from django_select2.forms import Select2MultipleWidget
from django.core.exceptions import ValidationError
from .services import CompanyService
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
        fields = [
            'company_name', 
            'nepali_name', 
            'phone_number', 
            'telephone_number', 
            'email', 
            'isactive',
            'remarks',           
            'blank_col1',        
            'blank_col2'         
        ]
        exclude = ['username']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
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
        from .services import CompanyService
        from django.core.exceptions import ValidationError, PermissionDenied
        
        username = self.cleaned_data.get('username', '').strip()
        password = self.cleaned_data.get('password', '').strip()
        group_ids = self.cleaned_data.get('group_ids', [])
        
        company_data = {
            'company_name': self.cleaned_data.get('company_name'),
            'nepali_name': self.cleaned_data.get('nepali_name'),
            'phone_number': self.cleaned_data.get('phone_number'),
            'telephone_number': self.cleaned_data.get('telephone_number'),
            'email': self.cleaned_data.get('email'),
            'isactive': self.cleaned_data.get('isactive'),
            'remarks': self.cleaned_data.get('remarks'),           
            'blank_col1': self.cleaned_data.get('blank_col1'),     
            'blank_col2': self.cleaned_data.get('blank_col2'), 
        }
        
        try:
            user = self.request.user if self.request else None

            if self.instance.pk:  # Update
                company = CompanyService.update_company(
                    company=self.instance,
                    username=username or None,
                    password=password or None,
                    company_data=company_data,
                    group_ids=group_ids,
                    groups_lookup=self.groups_lookup,
                    user = user
                )
            else:  # Create
                company = CompanyService.create_company(
                    username=username,
                    password=password,
                    company_data=company_data,
                    group_ids=group_ids,
                    groups_lookup=self.groups_lookup,
                    user= user
                )
        except (ValidationError, PermissionDenied) as e:
            self.add_error(None, str(e))
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
        
        try:
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
        except ValidationError as e:
            self.add_error(None, e)
            raise
        
        return individual

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username', '').strip()
        
        # Validate for new individuals
        if not self.instance.pk:
            if not username:
                raise forms.ValidationError("Username is required for new individuals")
            if not cleaned_data.get('password'):
                raise forms.ValidationError("Password is required for new individuals")
            
            # Check if username already exists
            if Account.objects.filter(username=username).exists():
                self.add_error('username', "This username is already in use.")
        else:
            # For existing individuals, check if new username conflicts
            if username:
                current_username = self.instance.username.username
                if username != current_username:
                    if Account.objects.filter(username=username).exists():
                        self.add_error('username', "This username is already in use.")
        
        return cleaned_data

    def save_m2m(self):
        pass


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    form = CompanyAdminForm
    list_display = ( "username", "company_name", "isactive")
    list_filter = ("isactive",)
    actions = ['soft_delete_selected', 'approve_selected']
    
    class Media:
        css = {
            'all': ('https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',)
        }
        js = ('https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js',)
    
    def has_add_permission(self, request):
        """UI check - service layer enforces"""
        return request.user.has_perm('main_system.add_company')
    
    def has_change_permission(self, request, obj=None):
        """UI check - service layer enforces"""
        return request.user.has_perm('main_system.change_company')
    
    def has_delete_permission(self, request, obj=None):
        """UI check - Admin only for hard delete"""
        return request.user.has_perm('main_system.delete_company')
    
    def delete_model(self, request, obj):
        """Hard delete - Admin only"""
        from .services import CompanyService
        CompanyService.hard_delete_company(obj, user=request.user)
    
    def delete_queryset(self, request, queryset):
        """Hard delete - Admin only"""
        from .services import CompanyService
        for company in queryset:
            CompanyService.hard_delete_company(company, user=request.user)

    def get_form(self, request, obj=None, **kwargs):
        """Pass request to form"""
        FormClass = super().get_form(request, obj, **kwargs)
        
        class FormWithRequest(FormClass):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return FormClass(*args, **kwargs)
        
        return FormWithRequest

    def soft_delete_selected(self, request, queryset):
        """Soft delete action"""
        from .services import CompanyService
        from django.contrib import messages
        from django.core.exceptions import PermissionDenied
        
        try:
            for company in queryset:
                CompanyService.soft_delete_company(company, user=request.user)
            messages.success(request, f"{queryset.count()} companies soft deleted successfully.")
        except PermissionDenied as e:
            messages.error(request, str(e))
    soft_delete_selected.short_description = "Soft delete selected companies"

    def approve_selected(self, request, queryset):
        """Approve action"""
        from .services import CompanyService
        from django.contrib import messages
        from django.core.exceptions import PermissionDenied
        
        try:
            for company in queryset:
                CompanyService.approve_company(company, user=request.user)
            messages.success(request, f"{queryset.count()} companies approved successfully.")
        except PermissionDenied as e:
            messages.error(request, str(e))
    approve_selected.short_description = "Approve selected companies"

    def get_actions(self, request):
        """Show actions based on permissions"""
        actions = super().get_actions(request)
        
        if not request.user.has_perm('main_system.soft_delete_company'):
            if 'soft_delete_selected' in actions:
                del actions['soft_delete_selected']
        
        if not request.user.has_perm('main_system.approve_company'):
            if 'approve_selected' in actions:
                del actions['approve_selected']
        
        return actions

@admin.register(Individual)
class IndividualAdmin(admin.ModelAdmin):
    form = IndividualAdminForm
    list_display = ( "user_full_name", "username", "get_group_name", "get_company_name")
    actions = ['soft_delete_selected', 'approve_selected']
    
    def get_company_name(self, obj):
        if obj.group_id and obj.group_id.company_id:
            return obj.group_id.company_id.company_name
        return "-"
    get_company_name.short_description = "Company Name"
    
    def get_group_name(self, obj):
        if obj.group_id:
            if obj.group_id.group_name:
                return obj.group_id.group_name
            elif obj.group_id.group_id:
                return f"Group {obj.group_id.group_id}"
        return "-"
    get_group_name.short_description = "Group Name"
    
    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm('main_system.delete_individual')
    
    def soft_delete_selected(self, request, queryset):
        from .services import IndividualService
        from django.contrib import messages
        from django.core.exceptions import PermissionDenied
        
        try:
            for individual in queryset:
                IndividualService.soft_delete_individual(individual, user=request.user)
            messages.success(request, f"{queryset.count()} individuals soft deleted successfully.")
        except PermissionDenied as e:
            messages.error(request, str(e))
    soft_delete_selected.short_description = "Soft delete selected individuals"
    
    def approve_selected(self, request, queryset):
        from .services import IndividualService
        from django.contrib import messages
        from django.core.exceptions import PermissionDenied
        
        try:
            for individual in queryset:
                IndividualService.approve_individual(individual, user=request.user)
            messages.success(request, f"{queryset.count()} individuals approved successfully.")
        except PermissionDenied as e:
            messages.error(request, str(e))
    approve_selected.short_description = "Approve selected individuals"
    
    def delete_model(self, request, obj):
        from .services import IndividualService
        IndividualService.hard_delete_individual(obj, user=request.user)
    
    def delete_queryset(self, request, queryset):
        from .services import IndividualService
        for individual in queryset:
            IndividualService.hard_delete_individual(individual, user=request.user)
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        
        if not request.user.has_perm('main_system.soft_delete_individual'):
            if 'soft_delete_selected' in actions:
                del actions['soft_delete_selected']
        
        if not request.user.has_perm('main_system.approve_individual'):
            if 'approve_selected' in actions:
                del actions['approve_selected']
        
        return actions
    
    def get_form(self, request, obj=None, **kwargs):
        """Pass request to form"""
        FormClass = super().get_form(request, obj, **kwargs)
        
        class FormWithRequest(FormClass):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return FormClass(*args, **kwargs)
        
        return FormWithRequest
    
@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("row_id", "group_id", "group_name", "company_id", "isactive", "isdeleted")
    list_filter = ("isactive", "isdeleted")

    def has_add_permission(self, request):
        return (request.user.is_superuser or 
                request.user.groups.filter(name__in=['Editor', 'Admin']).exists())
    
    def has_change_permission(self, request, obj=None):
        return (request.user.is_superuser or 
                request.user.groups.filter(name__in=['Editor', 'Approver', 'Admin']).exists())
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name='Admin').exists()


@admin.register(Account)
class AccountAdmin(BaseUserAdmin):
    list_display = ('username', 'is_active', 'is_staff', 'is_superuser', 'get_user_type','get_groups')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups') 
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser','groups')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'is_staff', 'is_superuser','groups'),
        }),
    )
    filter_horizontal = ('groups',)
    search_fields = ('username',)
    ordering = ('username',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('company_profile', 'individual_profile').prefetch_related('groups')
    
    def get_user_type(self, obj):
        return obj.get_user_type() or '-'
    get_user_type.short_description = 'User Type'
    
    def get_groups(self, obj):
        return ", ".join([g.name for g in obj.groups.all()]) or '-'
    get_groups.short_description = 'Staff Roles'
    
    def has_add_permission(self, request):
        # Only Admin role can add accounts directly
        return request.user.is_superuser or request.user.groups.filter(name='Admin').exists()
    
    def has_delete_permission(self, request, obj=None):
        # Only Admin role can delete accounts
        return request.user.is_superuser or request.user.groups.filter(name='Admin').exists()