import json
import os
import re
from django.http import JsonResponse #type: ignore
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin  #type: ignore
from django.contrib import admin #type: ignore
from django import forms #type: ignore
from django.conf import settings #type: ignore
from django_select2.forms import Select2MultipleWidget #type: ignore
from django.core.exceptions import ValidationError, PermissionDenied #type: ignore
from .services import CompanyService, IndividualService
from .models import AuditLog, Company, Group, Individual, Account
from django.contrib import messages  #type: ignore
from django.contrib.auth.models import Group as AuthGroup #type: ignore
from .utils import GroupAPIService
from django.shortcuts import redirect #type: ignore
from django.contrib.admin.views.decorators import staff_member_required #type: ignore
from .utils import validate_password_strength


admin.site.site_header = "Corporate Portal"
admin.site.site_title = "Corporate Portal"
admin.site.index_title = "Welcome to Corporate Portal"


@staff_member_required
def refresh_groups_cache_view(request):
    """Admin view to manually refresh groups cache - Superuser and Admin only"""
    
    # Check permissions
    if not request.user.is_superuser:
        user_groups = list(request.user.groups.values_list('name', flat=True))
        if 'Admin' not in user_groups:
            messages.error(request, "You don't have permission to refresh groups cache.")
            return redirect('admin:main_system_group_changelist')
    
    try:
        groups = GroupAPIService.refresh_cache()
        messages.success(request, f'Successfully refreshed {len(groups)} groups from API')
    except Exception as e:
        messages.error(request, f'Failed to refresh cache: {str(e)}')
    
    return redirect('admin:main_system_group_changelist')


# ============================================================
# COMPANY ADMIN FORM
# ============================================================

class CompanyAdminForm(forms.ModelForm):
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

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        # Load groups from API cache
        try:
            groups_data = GroupAPIService.get_groups()
        except Exception as e:
            groups_data = []
            if self.request:
                messages.warning(
                    self.request,
                    f"Failed to load groups from API: {str(e)}. Please try again later."
                )

        # Store groups lookup for later
        self.groups_lookup = {g['groupid']: g['groupname'] for g in groups_data}

        # Only set choices if group_ids field exists (not in readonly)
        if 'group_ids' in self.fields:
            choices = [(g['groupid'], f"{g['groupname']} ({g['groupid']})") for g in groups_data]
            self.fields['group_ids'].choices = choices

            # If editing, pre-populate with existing groups
            if self.instance and self.instance.pk:
                existing_groups = Group.objects.filter(company_id=self.instance, isdeleted=False)
                selected = [g.group_id for g in existing_groups if g.group_id]
                self.fields['group_ids'].initial = selected

                # Make group_ids readonly for Viewer and Approver
                if self.request and not self.request.user.is_superuser:
                    user_groups = self.request.user.groups.values_list('name', flat=True)
                    if 'Viewer' in user_groups or 'Approver' in user_groups:
                        self.fields['group_ids'].disabled = True
                        self.fields['group_ids'].help_text = "You don't have permission to modify groups"

    def save(self, commit=True):
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
                fresh_instance = Company.objects.get(pk=self.instance.pk)
                company = CompanyService.update_company(
                    company=fresh_instance,
                    company_data=company_data,
                    group_ids=group_ids,
                    groups_lookup=self.groups_lookup,
                    user=user
                )
            else:  # Create
                company = CompanyService.create_company(
                    company_data=company_data,
                    group_ids=group_ids,
                    groups_lookup=self.groups_lookup,
                    user=user
                )
        except (ValidationError, PermissionDenied) as e:
            self.add_error(None, str(e))
            raise

        return company

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


# ============================================================
# COMPANY ACCOUNT ADMIN FORM
# ============================================================

class CompanyAccountForm(forms.ModelForm):
    """Form for creating/editing company-linked accounts"""
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        required=False,
        help_text="Leave blank to keep current password. Required for new accounts."
    )

    class Meta:
        model = Account
        fields = ['username', 'company_id', 'is_active']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fields['company_id'].queryset = Company.objects.all()
        self.fields['company_id'].required = True
        self.fields['company_id'].label = "Company"

        widget = self.fields['company_id'].widget
        while widget is not None:
            for attr in ('can_add_related', 'can_change_related', 'can_delete_related', 'can_view_related'):
                if hasattr(widget, attr):
                    setattr(widget, attr, False)
            widget = getattr(widget, 'widget', None)

        # ← Guard: username may not be present if it's in readonly_fields
        if 'username' in self.fields and self.instance and self.instance.pk:
            self.fields['username'].disabled = True
            self.fields['username'].help_text = "Username cannot be changed after creation."

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password', '').strip()

        # Password required on create
        if not self.instance.pk:
            if not password:
                raise forms.ValidationError("Password is required for new accounts.")
            username = cleaned_data.get('username', '').strip()
            if not username:
                raise forms.ValidationError("Username is required.")
            if Account.objects.filter(username=username).exists():
                self.add_error('username', "This username is already in use.")

        # Password strength check
        if password:
            errors = validate_password_strength(password)
            if errors:
                raise forms.ValidationError(f"Password must contain: {', '.join(errors)}.")

        return cleaned_data

    def save(self, commit=True):
        user = self.request.user if self.request else None
        password = self.cleaned_data.get('password', '').strip()

        if self.instance.pk:
            # Update: only password and is_active can change
            account = self.instance
            if password:
                account.set_password(password)
            account.is_active = self.cleaned_data.get('is_active', True)
            account.company_id = self.cleaned_data.get('company_id')
            if user:
                account.modified_by = user.username
            account.save()

            if password and user:
                AuditLog.create_log(
                    action='password_reset',
                    target_username=account.username,
                    target_type='company',
                    performed_by=user.username,
                    details="Password changed via admin edit form",
                    ip_address=None
                )
        else:
            # Create new company account
            account = Account.objects.create_user(
                username=self.cleaned_data['username'],
                password=password,
                company_id=self.cleaned_data.get('company_id'),
                is_active=self.cleaned_data.get('is_active', True),
            )
            if user:
                account.created_by = user.username
                account.modified_by = user.username
                account.save()

                AuditLog.create_log(
                    action='create',
                    target_username=account.username,
                    target_type='company',
                    performed_by=user.username,
                    details=json.dumps({
                        'company': account.company_id.company_name if account.company_id else None,
                    }),
                    ip_address=None
                )

        return account

    def save_m2m(self):
        pass


# ============================================================
# INDIVIDUAL ADMIN FORM
# ============================================================

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
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if 'username' in self.fields and self.instance and self.instance.pk:
            self.fields['username'].initial = self.instance.username.username
            self.fields['username'].help_text = f"Current: {self.instance.username.username}. Leave blank to keep it."

    def save(self, commit=True):
        username = self.cleaned_data.get('username', '').strip()
        password = self.cleaned_data.get('password', '').strip()

        individual_data = {
            'group_id': self.cleaned_data.get('group_id'),
            'user_full_name': self.cleaned_data.get('user_full_name'),
        }

        try:
            user = self.request.user if self.request else None

            if self.instance.pk:  # Update
                individual = IndividualService.update_individual(
                    individual=self.instance,
                    username=username or None,
                    password=password or None,
                    individual_data=individual_data,
                    user=user
                )
            else:  # Create
                individual = IndividualService.create_individual(
                    username=username,
                    password=password,
                    individual_data=individual_data,
                    user=user
                )
        except (ValidationError, PermissionDenied) as e:
            self.add_error(None, str(e))
            raise

        return individual

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username', '').strip()

        if not self.instance.pk:
            if not username:
                raise forms.ValidationError("Username is required for new individuals")
            if not cleaned_data.get('password'):
                raise forms.ValidationError("Password is required for new individuals")
            if Account.objects.filter(username=username).exists():
                self.add_error('username', "This username is already in use.")
        else:
            if username:
                current_username = self.instance.username.username
                if username != current_username:
                    if Account.objects.filter(username=username).exists():
                        self.add_error('username', "This username is already in use.")

        return cleaned_data

    def save_m2m(self):
        pass


# ============================================================
# ACCOUNT ADMIN
# ============================================================

@admin.register(Account)
class AccountAdmin(BaseUserAdmin):
    list_display = ('username', 'is_active', 'is_staff', 'is_superuser', 'get_user_type', 'get_groups')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'groups')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'groups'),
        }),
    )

    filter_horizontal = ('groups',)
    search_fields = ('username',)
    ordering = ('username',)
    actions = ['reset_password_action']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('company_id', 'individual_profile')  # company_id is correct

        if not request.user.is_superuser:
            user_groups = list(request.user.groups.values_list('name', flat=True))
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                return qs.filter(username=request.user.username)
            if 'Editor' in user_groups:
                return qs.filter(is_staff=False)

        return qs

    def get_groups(self, obj):
        groups = list(obj.groups.all())
        return ", ".join([g.name for g in groups]) or '-'
    get_groups.short_description = 'Staff Roles'

    def get_user_type(self, obj):
        return obj.get_user_type() or '-'
    get_user_type.short_description = 'User Type'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        STAFF_ROLE_GROUPS = ['Viewer', 'Approver', 'Editor', 'Admin']

        if 'groups' in form.base_fields:
            if obj:
                user_type = obj.get_user_type()
                if user_type in ['company', 'individual']:
                    form.base_fields['groups'].queryset = AuthGroup.objects.none()
                    form.base_fields['groups'].help_text = "Staff roles cannot be assigned to company or individual accounts."
                    form.base_fields['groups'].disabled = True
                else:
                    # staff, admin, None, or anything else — always show staff role groups
                    form.base_fields['groups'].queryset = AuthGroup.objects.filter(name__in=STAFF_ROLE_GROUPS)
                    form.base_fields['groups'].help_text = "Select a role for this staff account."
            else:
                form.base_fields['groups'].queryset = AuthGroup.objects.filter(name__in=STAFF_ROLE_GROUPS)
                form.base_fields['groups'].help_text = "Only staff accounts can be assigned to these groups."

        return form

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets

        if request.user.is_superuser:
            return (
                (None, {'fields': ('username', 'password')}),
                ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')}),
            )
        else:
            user_groups = request.user.groups.values_list('name', flat=True)

            if 'Editor' in user_groups and obj and obj.is_staff:
                return (
                    (None, {'fields': ('username',)}),
                    ('Permissions', {'fields': ('is_active', 'is_staff', 'groups')}),
                )

            return (
                (None, {'fields': ('username', 'password')}),
                ('Permissions', {'fields': ('is_active', 'is_staff', 'groups')}),
            )

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)

        if obj:
            readonly = readonly + ('username', 'is_staff')  # ← both locked when editing

        if not request.user.is_superuser:
            user_groups = request.user.groups.values_list('name', flat=True)

            if 'Editor' in user_groups:
                if obj and obj.is_staff:
                    return readonly + ('username', 'is_active', 'is_staff', 'groups')

            if 'Viewer' in user_groups or 'Approver' in user_groups:
                if obj:
                    return readonly + ('username', 'is_active', 'is_staff', 'groups')

        return readonly

    def has_add_permission(self, request):
        return (request.user.is_superuser or
                request.user.groups.filter(name='Admin').exists())

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        user_groups = request.user.groups.values_list('name', flat=True)

        if 'Admin' in user_groups:
            if obj and obj.is_superuser:
                return False
            return True

        if 'Editor' in user_groups:
            return True

        if 'Viewer' in user_groups or 'Approver' in user_groups:
            if obj and obj.username == request.user.username:
                return True

        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        STAFF_ROLE_GROUPS = ['Viewer', 'Approver', 'Editor', 'Admin']

        old_is_staff = None
        old_is_superuser = None
        old_is_active = None
        old_password_hash = None

        if change and obj.pk:
            old_account = Account.objects.get(pk=obj.pk)
            form._old_groups = list(old_account.groups.values_list('name', flat=True))
            old_is_staff = old_account.is_staff
            old_is_superuser = old_account.is_superuser
            old_is_active = old_account.is_active
            old_password_hash = old_account.password
        else:
            form._old_groups = []
            obj.is_staff = True  # ← accounts created here are always staff

        if not request.user.is_superuser:
            obj.is_superuser = False

        # Prevent company/individual accounts from becoming staff/superuser
        user_type = obj.get_user_type()
        if user_type in ['company', 'individual']:
            if obj.is_superuser or obj.is_staff:
                messages.error(
                    request,
                    f"Cannot make {user_type} accounts into staff or superuser accounts. "
                    f"These flags have been reset to False."
                )
                obj.is_superuser = False
                obj.is_staff = False

        obj.modified_by = request.user.username
        super().save_model(request, obj, form, change)

        password_changed = False
        if change and old_password_hash and old_password_hash != obj.password:
            password_changed = True

        if 'groups' in form.cleaned_data:
            selected_groups = form.cleaned_data['groups']
            staff_role_groups = [g for g in selected_groups if g.name in STAFF_ROLE_GROUPS]

            if staff_role_groups:
                user_type = obj.get_user_type()
                if user_type in ['company', 'individual']:
                    obj.groups.remove(*staff_role_groups)
                    messages.warning(
                        request,
                        f"Staff roles cannot be assigned to {user_type} accounts. Groups have been removed."
                    )
                elif not obj.is_staff:
                    obj.groups.remove(*staff_role_groups)
                    messages.warning(
                        request,
                        "Staff roles can only be assigned to accounts with 'is_staff' enabled. Groups have been removed."
                    )

        if change:
            permission_changes = {}
            if old_is_staff != obj.is_staff:
                permission_changes['is_staff'] = {'old': old_is_staff, 'new': obj.is_staff}
            if old_is_superuser != obj.is_superuser:
                permission_changes['is_superuser'] = {'old': old_is_superuser, 'new': obj.is_superuser}
            if old_is_active != obj.is_active:
                permission_changes['is_active'] = {'old': old_is_active, 'new': obj.is_active}

            if permission_changes:
                AuditLog.create_log(
                    action='permission_change',
                    target_username=obj.username,
                    target_type=obj.get_user_type() or 'unknown',
                    performed_by=request.user.username,
                    details=json.dumps(permission_changes),
                    ip_address=request.META.get('REMOTE_ADDR')
                )

            if password_changed:
                AuditLog.create_log(
                    action='password_reset',
                    target_username=obj.username,
                    target_type=obj.get_user_type() or 'unknown',
                    performed_by=request.user.username,
                    details="Password changed via admin edit form",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
        else:
            AuditLog.create_log(
                action='create',
                target_username=obj.username,
                target_type=obj.get_user_type() or 'account',
                performed_by=request.user.username,
                details="Account created via admin interface",
                ip_address=request.META.get('REMOTE_ADDR')
            )

    def user_change_password(self, request, id, form_url=''):
        user = self.get_object(request, id)
        response = super().user_change_password(request, id, form_url)

        if response.status_code == 302:
            AuditLog.create_log(
                action='password_reset',
                target_username=user.username,
                target_type=user.get_user_type() or 'unknown',
                performed_by=request.user.username,
                details="Password changed via admin password change form",
                ip_address=request.META.get('REMOTE_ADDR')
            )

        return response

    def reset_password_action(self, request, queryset):
        user_groups = list(request.user.groups.values_list('name', flat=True))

        for account in queryset:
            if account.username == request.user.username:
                messages.warning(request, f"You cannot reset your own password: {account.username}")
                continue

            if account.is_staff:
                if not (request.user.is_superuser or 'Admin' in user_groups):
                    messages.error(request, f"You don't have permission to reset staff password: {account.username}")
                    continue
            else:
                if not (request.user.is_superuser or 'Editor' in user_groups or 'Admin' in user_groups):
                    messages.error(request, f"You don't have permission to reset password: {account.username}")
                    continue

            temp_password = Account.objects.make_random_password()
            account.set_password(temp_password)
            account.modified_by = request.user.username
            account.save()

            AuditLog.create_log(
                action='password_reset',
                target_username=account.username,
                target_type=account.get_user_type() or 'unknown',
                performed_by=request.user.username,
                details="Password reset via admin action. New temp password generated.",
                ip_address=request.META.get('REMOTE_ADDR')
            )

            messages.success(request, f"Password reset for {account.username}. New password: {temp_password}")
    reset_password_action.short_description = "Reset password for selected accounts"

    def get_actions(self, request):
        actions = super().get_actions(request)
        user_groups = request.user.groups.values_list('name', flat=True)

        if not (request.user.is_superuser or 'Editor' in user_groups or 'Admin' in user_groups):
            if 'reset_password_action' in actions:
                del actions['reset_password_action']

        return actions

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}

        if not request.user.is_superuser:
            user_groups = request.user.groups.values_list('name', flat=True)
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                extra_context['show_save'] = False
                extra_context['show_save_and_continue'] = False
                extra_context['show_save_and_add_another'] = False

        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        if change:
            obj = form.instance
            old_groups = getattr(form, '_old_groups', [])
            new_groups = list(obj.groups.values_list('name', flat=True))

            if set(old_groups) != set(new_groups):
                AuditLog.create_log(
                    action='role_change',
                    target_username=obj.username,
                    target_type=obj.get_user_type() or 'unknown',
                    performed_by=request.user.username,
                    details=json.dumps({
                        'old_groups': old_groups,
                        'new_groups': new_groups
                    }),
                    ip_address=request.META.get('REMOTE_ADDR')
                )


# ============================================================
# COMPANY ADMIN
# ============================================================

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    form = CompanyAdminForm
    list_display = ("company_name", "isactive", "get_account_count")
    list_filter = ("isactive",)
    actions = ['soft_delete_selected']
    search_fields = ['company_name']

    class Media:
        css = {
            'all': ('https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',)
        }
        js = ('https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js',)

    def get_form(self, request, obj=None, **kwargs):
        FormClass = super().get_form(request, obj, **kwargs)

        class FormWithRequest(FormClass):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return FormClass(*args, **kwargs)

        return FormWithRequest

    def get_account_count(self, obj):
        return Account.objects.filter(company_id=obj).count()
    get_account_count.short_description = "Linked Accounts"

    def group_ids(self, obj):
        if obj and obj.pk:
            groups = Group.objects.filter(company_id=obj, isdeleted=False)
            if groups.exists():
                return ", ".join([f"{g.group_name} ({g.group_id})" for g in groups])
        return "-"
    group_ids.short_description = "Groups"

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)

        if not request.user.is_superuser:
            user_groups = request.user.groups.values_list('name', flat=True)
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                model_fields = [field.name for field in self.model._meta.fields if field.name not in ['company_id']]
                form_fields = ['group_ids']
                return tuple(set(model_fields + form_fields))

        return readonly

    def has_add_permission(self, request):
        return (request.user.is_superuser or
                request.user.has_perm('main_system.add_company'))

    def has_change_permission(self, request, obj=None):
        return (request.user.is_superuser or
                request.user.has_perm('main_system.change_company') or
                request.user.has_perm('main_system.view_company'))

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def soft_delete_selected(self, request, queryset):
        try:
            for company in queryset:
                CompanyService.soft_delete_company(company, user=request.user)
            messages.success(request, f"{queryset.count()} companies soft deleted successfully.")
        except PermissionDenied as e:
            messages.error(request, str(e))
    soft_delete_selected.short_description = "Soft delete selected companies"

    def delete_model(self, request, obj):
        CompanyService.hard_delete_company(obj, user=request.user)

    def delete_queryset(self, request, queryset):
        for company in queryset:
            CompanyService.hard_delete_company(company, user=request.user)

    def get_actions(self, request):
        actions = super().get_actions(request)

        if not request.user.has_perm('main_system.soft_delete_company'):
            if 'soft_delete_selected' in actions:
                del actions['soft_delete_selected']

        return actions

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}

        if not request.user.is_superuser:
            user_groups = request.user.groups.values_list('name', flat=True)
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                extra_context['show_save'] = False
                extra_context['show_save_and_continue'] = False
                extra_context['show_save_and_add_another'] = False

        return super().change_view(request, object_id, form_url, extra_context=extra_context)


# ============================================================
# COMPANY ACCOUNT ADMIN  (proxy-based separate section)
# ============================================================

class CompanyAccount(Account):
    """Proxy model so company accounts get their own admin section"""
    class Meta:
        proxy = True
        verbose_name = "Company Account"
        verbose_name_plural = "Company Accounts"


@admin.register(CompanyAccount)
class CompanyAccountAdmin(admin.ModelAdmin):
    form = CompanyAccountForm
    list_display = ('username', 'get_company_name', 'is_active')
    list_filter = ('is_active', 'company_id')
    search_fields = ('username', 'company_id__company_name')
    actions = ['soft_delete_selected', 'reset_password_action']

    fieldsets = (
        (None, {'fields': ('username', 'company_id', 'is_active', 'password')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('username', 'company_id', 'is_active', 'password')}),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return self.fieldsets

    def get_form(self, request, obj=None, **kwargs):
        FormClass = super().get_form(request, obj, **kwargs)

        class FormWithRequest(FormClass):
            def __new__(cls, *args, **kw):
                kw['request'] = request
                return FormClass(*args, **kw)

        form = FormWithRequest

        if 'company_id' in form.base_fields:
            widget = form.base_fields['company_id'].widget
            for attr in ('can_add_related', 'can_change_related', 'can_delete_related'):
                if hasattr(widget, attr):
                    setattr(widget, attr, False)

        return form

    def get_queryset(self, request):
        qs = super().get_queryset(request).filter(
            company_id__isnull=False
        ).select_related('company_id')

        if not request.user.is_superuser:
            user_groups = list(request.user.groups.values_list('name', flat=True))
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                return qs.filter(username=request.user.username)

        return qs

    def get_company_name(self, obj):
        return obj.company_id.company_name if obj.company_id else '-'
    get_company_name.short_description = "Company"
    get_company_name.admin_order_field = 'company_id__company_name'

    def get_readonly_fields(self, request, obj=None):
        readonly = []
        if obj:
            readonly.append('username')

        if not request.user.is_superuser:
            user_groups = request.user.groups.values_list('name', flat=True)
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                return ['username', 'company_id', 'is_active', 'password']

        return readonly

    def has_add_permission(self, request):
        return (request.user.is_superuser or
                request.user.has_perm('main_system.add_account'))

    def has_change_permission(self, request, obj=None):
        return (request.user.is_superuser or
                request.user.has_perm('main_system.change_account') or
                request.user.has_perm('main_system.view_account'))

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def soft_delete_selected(self, request, queryset):
        if not (request.user.is_superuser or request.user.has_perm('main_system.change_account')):
            messages.error(request, "You don't have permission to deactivate accounts.")
            return

        for account in queryset:
            account.is_active = False
            account.modified_by = request.user.username
            account.save()
            AuditLog.create_log(
                action='soft_delete',
                target_username=account.username,
                target_type='company',
                performed_by=request.user.username,
                details=f"Company account '{account.username}' deactivated via admin action"
            )
        messages.success(request, f"{queryset.count()} company account(s) deactivated.")
    soft_delete_selected.short_description = "Deactivate selected company accounts"

    def reset_password_action(self, request, queryset):
        if not (request.user.is_superuser or
                request.user.has_perm('main_system.change_account') or
                request.user.groups.filter(name__in=['Admin', 'Editor']).exists()):
            messages.error(request, "You don't have permission to reset passwords.")
            return

        for account in queryset:
            temp_password = Account.objects.make_random_password()
            account.set_password(temp_password)
            account.modified_by = request.user.username
            account.save()

            AuditLog.create_log(
                action='password_reset',
                target_username=account.username,
                target_type='company',
                performed_by=request.user.username,
                details="Password reset via admin action. New temp password generated.",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f"Password reset for {account.username}. New password: {temp_password}")
    reset_password_action.short_description = "Reset password for selected company accounts"

    def get_actions(self, request):
        actions = super().get_actions(request)

        if not (request.user.is_superuser or
                request.user.has_perm('main_system.change_account') or
                request.user.groups.filter(name__in=['Admin', 'Editor']).exists()):
            if 'soft_delete_selected' in actions:
                del actions['soft_delete_selected']
            if 'reset_password_action' in actions:
                del actions['reset_password_action']

        return actions

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}

        if not request.user.is_superuser:
            user_groups = request.user.groups.values_list('name', flat=True)
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                extra_context['show_save'] = False
                extra_context['show_save_and_continue'] = False
                extra_context['show_save_and_add_another'] = False

        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        """save_model is bypassed — CompanyAccountForm.save() handles everything"""
        pass


# ============================================================
# INDIVIDUAL ADMIN
# ============================================================

@admin.register(Individual)
class IndividualAdmin(admin.ModelAdmin):
    form = IndividualAdminForm
    list_display = ("user_full_name", "username", "get_group_name", "get_company_name")
    actions = ['soft_delete_selected', 'reset_password_action']
    raw_id_fields = ('group_id',)
    autocomplete_fields = ['group_id']

    def get_form(self, request, obj=None, **kwargs):
        FormClass = super().get_form(request, obj, **kwargs)

        class FormWithRequest(FormClass):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return FormClass(*args, **kwargs)

        return FormWithRequest

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

    def username(self, obj):
        if obj and obj.username:
            return obj.username.username
        return "-"
    username.short_description = "Username"

    def password(self, obj):
        return "••••••••"
    password.short_description = "Password"

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)

        if not request.user.is_superuser:
            user_groups = request.user.groups.values_list('name', flat=True)
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                model_fields = [field.name for field in self.model._meta.fields if field.name not in ['user_id']]
                form_fields = ['username', 'password']
                return tuple(set(model_fields + form_fields))

        return readonly

    def has_add_permission(self, request):
        return (request.user.is_superuser or
                request.user.has_perm('main_system.add_individual'))

    def has_change_permission(self, request, obj=None):
        return (request.user.is_superuser or
                request.user.has_perm('main_system.change_individual') or
                request.user.has_perm('main_system.view_individual'))

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def soft_delete_selected(self, request, queryset):
        try:
            for individual in queryset:
                IndividualService.soft_delete_individual(individual, user=request.user)
            messages.success(request, f"{queryset.count()} individuals soft deleted successfully.")
        except PermissionDenied as e:
            messages.error(request, str(e))
    soft_delete_selected.short_description = "Soft delete selected individuals"

    def reset_password_action(self, request, queryset):
        if not (request.user.is_superuser or request.user.has_perm('main_system.reset_individual_password')):
            messages.error(request, "You don't have permission to reset passwords.")
            return

        for individual in queryset:
            temp_password = Account.objects.make_random_password()
            individual.username.set_password(temp_password)
            individual.username.save()
            messages.success(request, f"Password reset for {individual.user_full_name or individual.username.username}. New password: {temp_password}")
    reset_password_action.short_description = "Reset password for selected individuals"

    def delete_model(self, request, obj):
        IndividualService.hard_delete_individual(obj, user=request.user)

    def delete_queryset(self, request, queryset):
        for individual in queryset:
            IndividualService.hard_delete_individual(individual, user=request.user)

    def get_actions(self, request):
        actions = super().get_actions(request)

        if not request.user.has_perm('main_system.soft_delete_individual'):
            if 'soft_delete_selected' in actions:
                del actions['soft_delete_selected']

        if not request.user.has_perm('main_system.reset_individual_password'):
            if 'reset_password_action' in actions:
                del actions['reset_password_action']

        return actions

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}

        if not request.user.is_superuser:
            user_groups = request.user.groups.values_list('name', flat=True)
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                extra_context['show_save'] = False
                extra_context['show_save_and_continue'] = False
                extra_context['show_save_and_add_another'] = False

        return super().change_view(request, object_id, form_url, extra_context=extra_context)


# ============================================================
# AUDIT LOG ADMIN
# ============================================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'target_username', 'target_type', 'performed_by')
    list_filter = ('action', 'target_type', 'timestamp')
    search_fields = ('target_username', 'performed_by', 'details')
    readonly_fields = ('log_id', 'action', 'target_username', 'target_type', 'performed_by', 'timestamp', 'details')

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        user_groups = list(request.user.groups.values_list('name', flat=True))
        if 'Admin' in user_groups:
            return qs

        return qs.none()

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        user_groups = list(request.user.groups.values_list('name', flat=True))
        if any(role in user_groups for role in ['Admin', 'Editor', 'Viewer', 'Approver']):
            return True

        return False

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser or request.user.is_staff:
            return True
        return False

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True

        user_groups = list(request.user.groups.values_list('name', flat=True))
        if 'Admin' in user_groups:
            return True


# ============================================================
# GROUP ADMIN
# ============================================================

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("group_name", "company_id", "isactive", "isdeleted")
    list_filter = ("isactive", "isdeleted")
    actions = ['soft_delete_selected']
    search_fields = ['group_id', 'group_name']

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        show_refresh_button = False
        if request.user.is_superuser:
            show_refresh_button = True
        else:
            user_groups = list(request.user.groups.values_list('name', flat=True))
            if 'Admin' in user_groups:
                show_refresh_button = True

        extra_context['show_refresh_cache_button'] = show_refresh_button
        return super().changelist_view(request, extra_context=extra_context)

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)

        if not request.user.is_superuser:
            user_groups = request.user.groups.values_list('name', flat=True)
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                return [field.name for field in self.model._meta.fields if field.name != 'row_id']

        return readonly

    def has_add_permission(self, request):
        return (request.user.is_superuser or
                request.user.has_perm('main_system.add_group'))

    def has_change_permission(self, request, obj=None):
        return (request.user.is_superuser or
                request.user.has_perm('main_system.change_group') or
                request.user.has_perm('main_system.view_group'))

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def soft_delete_selected(self, request, queryset):
        if not request.user.has_perm('main_system.soft_delete_group'):
            messages.error(request, "You don't have permission to soft delete groups.")
            return

        queryset.update(isdeleted=True, isactive=False, modified_by=request.user.username)
        messages.success(request, f"{queryset.count()} groups soft deleted successfully.")
    soft_delete_selected.short_description = "Soft delete selected groups"

    def get_actions(self, request):
        actions = super().get_actions(request)

        if not request.user.has_perm('main_system.soft_delete_group'):
            if 'soft_delete_selected' in actions:
                del actions['soft_delete_selected']

        return actions

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}

        if not request.user.is_superuser:
            user_groups = request.user.groups.values_list('name', flat=True)
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                extra_context['show_save'] = False
                extra_context['show_save_and_continue'] = False
                extra_context['show_save_and_add_another'] = False

        return super().change_view(request, object_id, form_url, extra_context=extra_context)