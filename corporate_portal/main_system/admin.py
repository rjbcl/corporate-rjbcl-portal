import json

from django.contrib import admin, messages  # type: ignore
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin  # type: ignore
from django.contrib.auth.models import Group as AuthGroup  # type: ignore
from django.contrib.admin.views.decorators import staff_member_required  # type: ignore
from django.core.exceptions import ValidationError, PermissionDenied  # type: ignore
from django.shortcuts import redirect  # type: ignore
from django import forms  # type: ignore

from .models import (
    AuditLog, Company, CompanyDocument, Group,
    Account, CompanyAccount, UserVerification,
)
from .services import CompanyService, CompanyAccountService
from .utils import GroupAPIService, validate_password_strength

from django_select2.forms import Select2MultipleWidget  # type: ignore


admin.site.site_header = "Corporate Portal"
admin.site.site_title = "Corporate Portal"
admin.site.index_title = "Welcome to Corporate Portal"


# ============================================================
# HELPERS
# ============================================================

def _is_admin_or_super(user):
    return user.is_superuser or user.groups.filter(name='Admin').exists()

def _is_editor_or_above(user):
    return user.is_superuser or user.groups.filter(name__in=['Admin', 'Editor']).exists()

def _is_viewer_or_approver(user):
    return (
        not user.is_superuser and
        user.groups.filter(name__in=['Viewer', 'Approver']).exists()
    )


# ============================================================
# CACHE REFRESH VIEW
# ============================================================

@staff_member_required
def refresh_groups_cache_view(request):
    """Admin view to manually refresh groups cache — superuser and Admin only."""
    if not _is_admin_or_super(request.user):
        messages.error(request, "You don't have permission to refresh groups cache.")
        return redirect('admin:main_system_group_changelist')

    try:
        groups = GroupAPIService.refresh_cache()
        messages.success(request, f'Successfully refreshed {len(groups)} groups from API.')
    except Exception as e:
        messages.error(request, f'Failed to refresh cache: {str(e)}')

    return redirect('admin:main_system_group_changelist')


# ============================================================
# COMPANY DOCUMENT INLINE
# ============================================================

class CompanyDocumentInline(admin.StackedInline):
    """
    Inline for CompanyDocument under CompanyAdmin.
    Documents are submitted by the primary company user via the portal,
    but Admin/Editor/superuser can also manage them here.

    Permissions:
      Superuser / Admin : full edit + add + delete
      Editor            : add + edit (no delete)
      Viewer / Approver : readonly
    """
    model = CompanyDocument
    extra = 0
    can_delete = False  # controlled per-role in has_delete_permission

    fields = (
        'authorized_by',
        'business_purpose',
        'signature',
        'stamp',
        'official_request_letter',
    )

    readonly_fields_for_viewer = (
        'authorized_by',
        'business_purpose',
        'signature',
        'stamp',
        'official_request_letter',
    )

    def get_readonly_fields(self, request, obj=None):
        if _is_viewer_or_approver(request.user):
            return self.readonly_fields_for_viewer
        return ()

    def has_add_permission(self, request, obj=None):
        return _is_editor_or_above(request.user)

    def has_change_permission(self, request, obj=None):
        return _is_editor_or_above(request.user) or _is_viewer_or_approver(request.user)

    def has_delete_permission(self, request, obj=None):
        return _is_admin_or_super(request.user)

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user.username
        obj.modified_by = request.user.username
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if not instance.pk:
                instance.created_by = request.user.username
            instance.modified_by = request.user.username
            instance.save()
        formset.save_m2m()


# ============================================================
# COMPANY ADMIN FORM
# ============================================================

class CompanyAdminForm(forms.ModelForm):
    group_ids = forms.MultipleChoiceField(
        required=False,
        widget=Select2MultipleWidget(attrs={
            'data-placeholder': 'Search and select groups...',
            'style': 'width: 100%;',
        }),
        help_text="Search and select groups for this company.",
    )

    class Meta:
        model = Company
        fields = [
            # Company Information fieldset
            'company_name',
            'nepali_name',
            'phone_number',
            'telephone_number',
            'email',
            'isactive',
            'remarks',
            'blankcol',
            # Primary Contact fieldset
            'pan_number',
            'primary_contact_person',
            'primary_person_mobile',
            'primary_person_email',
        ]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        try:
            groups_data = GroupAPIService.get_groups()
        except Exception as e:
            groups_data = []
            if self.request:
                messages.warning(
                    self.request,
                    f"Failed to load groups from API: {str(e)}. Please try again later."
                )

        self.groups_lookup = {g['groupid']: g['groupname'] for g in groups_data}

        if 'group_ids' in self.fields:
            self.fields['group_ids'].choices = [
                (g['groupid'], f"{g['groupname']} ({g['groupid']})")
                for g in groups_data
            ]

            if self.instance and self.instance.pk:
                self.fields['group_ids'].initial = [
                    g.group_id
                    for g in Group.objects.filter(company=self.instance, isdeleted=False)
                    if g.group_id
                ]

                if self.request and _is_viewer_or_approver(self.request.user):
                    self.fields['group_ids'].disabled = True
                    self.fields['group_ids'].help_text = (
                        "You don't have permission to modify groups."
                    )

    def clean_group_ids(self):
        selected_group_ids = self.cleaned_data.get('group_ids', [])

        if selected_group_ids:
            existing_groups = Group.objects.filter(
                group_id__in=selected_group_ids,
                isdeleted=False,
            )
            if self.instance.pk:
                existing_groups = existing_groups.exclude(company=self.instance)

            if existing_groups.exists():
                conflicts = [
                    f"{g.group_id} ({g.group_name}) - already assigned to "
                    f"{g.company.company_name}"
                    for g in existing_groups
                ]
                raise forms.ValidationError(
                    f"The following groups are already assigned to other companies: "
                    f"{', '.join(conflicts)}"
                )

        return selected_group_ids

    def save(self, commit=True):
        group_ids = self.cleaned_data.get('group_ids', [])
        company_data = {
            'company_name':           self.cleaned_data.get('company_name'),
            'nepali_name':            self.cleaned_data.get('nepali_name'),
            'phone_number':           self.cleaned_data.get('phone_number'),
            'telephone_number':       self.cleaned_data.get('telephone_number'),
            'email':                  self.cleaned_data.get('email'),
            'isactive':               self.cleaned_data.get('isactive'),
            'remarks':                self.cleaned_data.get('remarks'),
            'blankcol':               self.cleaned_data.get('blankcol'),
            'pan_number':             self.cleaned_data.get('pan_number'),
            'primary_contact_person': self.cleaned_data.get('primary_contact_person'),
            'primary_person_mobile':  self.cleaned_data.get('primary_person_mobile'),
            'primary_person_email':   self.cleaned_data.get('primary_person_email'),
        }

        try:
            user = self.request.user if self.request else None

            if self.instance.pk:
                fresh_instance = Company.objects.get(pk=self.instance.pk)
                company = CompanyService.update_company(
                    company=fresh_instance,
                    company_data=company_data,
                    group_ids=group_ids,
                    groups_lookup=self.groups_lookup,
                    user=user,
                )
            else:
                company = CompanyService.create_company(
                    company_data=company_data,
                    group_ids=group_ids,
                    groups_lookup=self.groups_lookup,
                    user=user,
                )
        except (ValidationError, PermissionDenied) as e:
            self.add_error(None, str(e))
            raise

        return company

    def save_m2m(self):
        pass


# ============================================================
# COMPANY ACCOUNT ADMIN FORM
# ============================================================

class CompanyAccountAdminForm(forms.ModelForm):
    """
    Form for creating and editing company staff accounts.
    Manages Account (username, is_active, password) and
    CompanyAccount (profile fields) together.
    """
    username = forms.CharField(max_length=100, required=True)
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        required=False,
        help_text="Required for new accounts. Leave blank to keep current password.",
    )
    is_active = forms.BooleanField(required=False, initial=True)

    class Meta:
        model = CompanyAccount
        fields = [
            'company',
            'full_name',
            'mobile',
            'email',
            'designation',
            'department',
            'is_primary',
            'is_approved',
        ]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fields['company'].queryset = Company.objects.filter(isactive=True)
        self.fields['company'].required = True

        widget = self.fields['company'].widget
        for attr in ('can_add_related', 'can_change_related',
                     'can_delete_related', 'can_view_related'):
            if hasattr(widget, attr):
                setattr(widget, attr, False)

        if self.instance and self.instance.pk:
            account = self.instance.account
            self.initial['username'] = account.username
            self.initial['is_active'] = account.is_active
            if 'username' in self.fields:
                self.fields['username'].disabled = True
                self.fields['username'].help_text = "Username cannot be changed after creation."

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if self.instance and self.instance.pk:
            return self.instance.account.username
        if Account.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already in use.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password', '').strip()
        if not self.instance.pk and not password:
            raise forms.ValidationError("Password is required for new accounts.")
        if password:
            errors = validate_password_strength(password)
            if errors:
                raise forms.ValidationError(
                    f"Password must contain: {', '.join(errors)}."
                )
        return password

    def save(self, commit=True):
        user = self.request.user if self.request else None
        password = self.cleaned_data.get('password', '').strip()
        is_active = self.cleaned_data.get('is_active', True)

        profile_data = {
            'company':     self.cleaned_data.get('company'),
            'full_name':   self.cleaned_data.get('full_name'),
            'mobile':      self.cleaned_data.get('mobile'),
            'email':       self.cleaned_data.get('email'),
            'designation': self.cleaned_data.get('designation'),
            'department':  self.cleaned_data.get('department'),
            'is_primary':  self.cleaned_data.get('is_primary', False),
        }

        try:
            if self.instance.pk:
                company_account = CompanyAccountService.update_company_account(
                    company_account=self.instance,
                    password=password or None,
                    profile_data=profile_data,
                    user=user,
                )
                if company_account.account.is_active != is_active:
                    company_account.account.is_active = is_active
                    if user:
                        company_account.account.modified_by = user.username
                    company_account.account.save()
            else:
                company_account = CompanyAccountService.create_company_account(
                    username=self.cleaned_data.get('username'),
                    password=password,
                    profile_data=profile_data,
                    user=user,
                )
                if not is_active:
                    company_account.account.is_active = False
                    company_account.account.save()

        except (ValidationError, PermissionDenied) as e:
            self.add_error(None, str(e))
            raise

        return company_account

    def save_m2m(self):
        pass


# ============================================================
# ACCOUNT ADMIN  (staff and admin accounts only)
# ============================================================

@admin.register(Account)
class AccountAdmin(BaseUserAdmin):
    list_display = ('username', 'is_active', 'is_staff', 'is_superuser', 'get_groups')
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
        """Staff and admin accounts only — company accounts have their own section."""
        qs = super().get_queryset(request).filter(is_staff=True)

        if not request.user.is_superuser:
            user_groups = list(request.user.groups.values_list('name', flat=True))
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                return qs.filter(username=request.user.username)
            if 'Editor' in user_groups:
                return qs.filter(is_superuser=False)

        return qs

    def get_groups(self, obj):
        return ", ".join(obj.groups.values_list('name', flat=True)) or '-'
    get_groups.short_description = 'Staff Roles'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        STAFF_ROLE_GROUPS = ['Viewer', 'Approver', 'Editor', 'Admin']

        if 'groups' in form.base_fields:
            form.base_fields['groups'].queryset = AuthGroup.objects.filter(
                name__in=STAFF_ROLE_GROUPS
            )
            form.base_fields['groups'].help_text = "Select a role for this staff account."

        return form

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets

        if request.user.is_superuser:
            return (
                (None, {'fields': ('username', 'password')}),
                ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')}),
            )

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
            readonly = readonly + ('username', 'is_staff')

        if not request.user.is_superuser:
            user_groups = request.user.groups.values_list('name', flat=True)
            if 'Editor' in user_groups and obj and obj.is_staff:
                return readonly + ('username', 'is_active', 'is_staff', 'groups')
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                if obj:
                    return readonly + ('username', 'is_active', 'is_staff', 'groups')

        return readonly

    def has_add_permission(self, request):
        return _is_admin_or_super(request.user)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        user_groups = request.user.groups.values_list('name', flat=True)
        if 'Admin' in user_groups:
            return not (obj and obj.is_superuser)
        if 'Editor' in user_groups:
            return True
        if 'Viewer' in user_groups or 'Approver' in user_groups:
            return obj and obj.username == request.user.username
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        old_is_staff = old_is_superuser = old_is_active = old_password_hash = None

        if change and obj.pk:
            old = Account.objects.get(pk=obj.pk)
            form._old_groups = list(old.groups.values_list('name', flat=True))
            old_is_staff = old.is_staff
            old_is_superuser = old.is_superuser
            old_is_active = old.is_active
            old_password_hash = old.password
        else:
            form._old_groups = []
            obj.is_staff = True

        if not request.user.is_superuser:
            obj.is_superuser = False

        obj.modified_by = request.user.username
        super().save_model(request, obj, form, change)

        password_changed = (
            change and old_password_hash and old_password_hash != obj.password
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
                    target_type='staff',
                    performed_by=request.user.username,
                    details=json.dumps(permission_changes),
                    ip_address=request.META.get('REMOTE_ADDR'),
                )

            if password_changed:
                AuditLog.create_log(
                    action='password_reset',
                    target_username=obj.username,
                    target_type='staff',
                    performed_by=request.user.username,
                    details="Password changed via admin edit form.",
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
        else:
            AuditLog.create_log(
                action='create',
                target_username=obj.username,
                target_type='staff',
                performed_by=request.user.username,
                details="Staff account created via admin interface.",
                ip_address=request.META.get('REMOTE_ADDR'),
            )

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
                    target_type='staff',
                    performed_by=request.user.username,
                    details=json.dumps({
                        'old_groups': old_groups,
                        'new_groups': new_groups,
                    }),
                    ip_address=request.META.get('REMOTE_ADDR'),
                )

    def user_change_password(self, request, id, form_url=''):
        user = self.get_object(request, id)
        response = super().user_change_password(request, id, form_url)

        if response.status_code == 302:
            AuditLog.create_log(
                action='password_reset',
                target_username=user.username,
                target_type='staff',
                performed_by=request.user.username,
                details="Password changed via admin password change form.",
                ip_address=request.META.get('REMOTE_ADDR'),
            )

        return response

    def reset_password_action(self, request, queryset):
        user_groups = list(request.user.groups.values_list('name', flat=True))

        for account in queryset:
            if account.username == request.user.username:
                messages.warning(request, f"You cannot reset your own password: {account.username}")
                continue

            if not _is_admin_or_super(request.user):
                messages.error(request, f"You don't have permission to reset staff password: {account.username}")
                continue

            temp_password = Account.objects.make_random_password()
            account.set_password(temp_password)
            account.modified_by = request.user.username
            account.save()

            AuditLog.create_log(
                action='password_reset',
                target_username=account.username,
                target_type='staff',
                performed_by=request.user.username,
                details="Password reset via admin action.",
                ip_address=request.META.get('REMOTE_ADDR'),
            )

            messages.success(request, f"Password reset for {account.username}. New password: {temp_password}")
    reset_password_action.short_description = "Reset password for selected accounts"

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not _is_admin_or_super(request.user):
            actions.pop('reset_password_action', None)
        return actions

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        if _is_viewer_or_approver(request.user):
            extra_context['show_save'] = False
            extra_context['show_save_and_continue'] = False
            extra_context['show_save_and_add_another'] = False
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


# ============================================================
# COMPANY ADMIN
# ============================================================

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    form = CompanyAdminForm
    inlines = [CompanyDocumentInline]
    list_display = ('company_name', 'isactive', 'get_account_count')
    list_filter = ('isactive',)
    search_fields = ('company_name',)
    actions = ['soft_delete_selected']

    # Two fieldsets — Company Information and Primary Contact
    fieldsets = (
        ('Company Information', {
            'fields': (
                'company_name',
                'nepali_name',
                'phone_number',
                'telephone_number',
                'email',
                'isactive',
                'remarks',
                'blankcol',
                'group_ids',
            ),
        }),
        ('Primary Contact', {
            'fields': (
                'pan_number',
                'primary_contact_person',
                'primary_person_mobile',
                'primary_person_email',
            ),
        }),
    )

    class Media:
        css = {
            'all': (
                'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/css/select2.min.css',
            )
        }
        js = (
            'https://cdn.jsdelivr.net/npm/select2@4.1.0-rc.0/dist/js/select2.min.js',
        )

    def get_form(self, request, obj=None, **kwargs):
        FormClass = super().get_form(request, obj, **kwargs)

        class FormWithRequest(FormClass):
            def __init__(self, *args, **kw):
                kw['request'] = request
                super().__init__(*args, **kw)

        return FormWithRequest

    def get_account_count(self, obj):
        return CompanyAccount.objects.filter(company=obj).count()
    get_account_count.short_description = "Linked Accounts"

    def get_readonly_fields(self, request, obj=None):
        if _is_viewer_or_approver(request.user):
            # Everything readonly for viewers/approvers
            model_fields = [
                f.name for f in self.model._meta.fields
                if f.name != 'company_id'
            ]
            return tuple(set(model_fields + ['group_ids']))

        return super().get_readonly_fields(request, obj)

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.has_perm('main_system.add_company')

    def has_change_permission(self, request, obj=None):
        return (
            request.user.is_superuser or
            request.user.has_perm('main_system.change_company') or
            request.user.has_perm('main_system.view_company')
        )

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
            actions.pop('soft_delete_selected', None)
        return actions

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        if _is_viewer_or_approver(request.user):
            extra_context['show_save'] = False
            extra_context['show_save_and_continue'] = False
            extra_context['show_save_and_add_another'] = False
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


# ============================================================
# COMPANY ACCOUNT ADMIN
# ============================================================

@admin.register(CompanyAccount)
class CompanyAccountAdmin(admin.ModelAdmin):
    form = CompanyAccountAdminForm
    list_display = (
        'get_username', 'get_company_name', 'full_name',
        'is_primary', 'is_approved', 'get_is_active', 'get_totp_status',
    )
    list_filter = ('company', 'is_primary', 'is_approved')
    search_fields = ('account__username', 'company__company_name', 'full_name')
    actions = ['approve_accounts', 'soft_delete_selected', 'reset_password_action']

    fieldsets = (
        ('Account', {
            'fields': ('username', 'password', 'is_active'),
        }),
        ('Company Profile', {
            'fields': (
                'company', 'full_name', 'mobile',
                'email', 'designation', 'department', 'is_primary', 'is_approved',
            ),
        }),
    )
    add_fieldsets = (
        ('Account', {
            'classes': ('wide',),
            'fields': ('username', 'password', 'is_active'),
        }),
        ('Company Profile', {
            'fields': (
                'company', 'full_name', 'mobile',
                'email', 'designation', 'department', 'is_primary', 'is_approved',
            ),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        return self.add_fieldsets if not obj else self.fieldsets

    def get_form(self, request, obj=None, **kwargs):
        FormClass = super().get_form(request, obj, **kwargs)

        class FormWithRequest(FormClass):
            def __init__(self, *args, **kw):
                kw['request'] = request
                super().__init__(*args, **kw)

        return FormWithRequest

    def get_queryset(self, request):
        qs = CompanyAccount.objects.all().select_related('account', 'company')

        if not request.user.is_superuser:
            user_groups = list(request.user.groups.values_list('name', flat=True))
            if 'Viewer' in user_groups or 'Approver' in user_groups:
                return qs.filter(account__username=request.user.username)

        return qs

    def get_username(self, obj):
        return obj.account.username
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'account__username'

    def get_company_name(self, obj):
        return obj.company.company_name
    get_company_name.short_description = 'Company'
    get_company_name.admin_order_field = 'company__company_name'

    def get_is_active(self, obj):
        return obj.account.is_active
    get_is_active.short_description = 'Active'
    get_is_active.boolean = True

    def get_totp_status(self, obj):
        try:
            return "Enabled" if obj.account.user_verification.is_totp_enabled else "Disabled"
        except UserVerification.DoesNotExist:
            return "Not Set Up"
    get_totp_status.short_description = 'TOTP'

    def get_readonly_fields(self, request, obj=None):
        readonly = []
        if _is_viewer_or_approver(request.user):
            return [
                'password', 'is_active', 'company',
                'full_name', 'mobile', 'email',
                'designation', 'department', 'is_primary', 'is_approved',
            ]
        return readonly

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.has_perm('main_system.add_companyaccount')

    def has_change_permission(self, request, obj=None):
        return (
            request.user.is_superuser or
            request.user.has_perm('main_system.change_companyaccount') or
            request.user.has_perm('main_system.view_companyaccount')
        )

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def approve_accounts(self, request, queryset):
        """Approve selected pending company accounts."""
        if not (request.user.is_superuser or
                request.user.has_perm('main_system.approve_company_account')):
            messages.error(request, "You don't have permission to approve accounts.")
            return

        approved = 0
        for company_account in queryset:
            if company_account.is_approved:
                messages.warning(
                    request,
                    f"{company_account.account.username} is already approved."
                )
                continue
            try:
                CompanyAccountService.approve_company_account(
                    company_account, user=request.user
                )
                approved += 1
            except Exception as e:
                messages.error(request, f"Failed to approve {company_account.account.username}: {str(e)}")

        if approved:
            messages.success(request, f"{approved} account(s) approved successfully.")
    approve_accounts.short_description = "Approve selected company accounts"

    def soft_delete_selected(self, request, queryset):
        try:
            for company_account in queryset:
                CompanyAccountService.soft_delete_company_account(
                    company_account, user=request.user
                )
            messages.success(request, f"{queryset.count()} company accounts soft deleted successfully.")
        except PermissionDenied as e:
            messages.error(request, str(e))
    soft_delete_selected.short_description = "Soft delete selected company accounts"

    def reset_password_action(self, request, queryset):
        if not (request.user.is_superuser or
                request.user.has_perm('main_system.reset_company_account_password')):
            messages.error(request, "You don't have permission to reset passwords.")
            return

        for company_account in queryset:
            if company_account.account.username == request.user.username:
                messages.warning(request, f"You cannot reset your own password: {company_account.account.username}")
                continue

            temp_password = Account.objects.make_random_password()
            try:
                CompanyAccountService.reset_password(
                    company_account, temp_password, user=request.user
                )
                messages.success(
                    request,
                    f"Password reset for {company_account.account.username}. "
                    f"New password: {temp_password}"
                )
            except PermissionDenied as e:
                messages.error(request, str(e))
    reset_password_action.short_description = "Reset password for selected accounts"

    def delete_model(self, request, obj):
        CompanyAccountService.hard_delete_company_account(obj, user=request.user)

    def delete_queryset(self, request, queryset):
        for company_account in queryset:
            CompanyAccountService.hard_delete_company_account(company_account, user=request.user)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm('main_system.soft_delete_company_account'):
            actions.pop('soft_delete_selected', None)
        if not request.user.has_perm('main_system.reset_company_account_password'):
            actions.pop('reset_password_action', None)
        return actions

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        if _is_viewer_or_approver(request.user):
            extra_context['show_save'] = False
            extra_context['show_save_and_continue'] = False
            extra_context['show_save_and_add_another'] = False
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


# ============================================================
# GROUP ADMIN
# ============================================================

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('group_name', 'company', 'isactive', 'isdeleted')
    list_filter = ('isactive', 'isdeleted')
    search_fields = ('group_id', 'group_name')
    actions = ['soft_delete_selected']

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_refresh_cache_button'] = _is_admin_or_super(request.user)
        return super().changelist_view(request, extra_context=extra_context)

    def get_readonly_fields(self, request, obj=None):
        if _is_viewer_or_approver(request.user):
            return [f.name for f in self.model._meta.fields if f.name != 'row_id']
        return super().get_readonly_fields(request, obj)

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.has_perm('main_system.add_group')

    def has_change_permission(self, request, obj=None):
        return (
            request.user.is_superuser or
            request.user.has_perm('main_system.change_group') or
            request.user.has_perm('main_system.view_group')
        )

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
            actions.pop('soft_delete_selected', None)
        return actions

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        if _is_viewer_or_approver(request.user):
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
    readonly_fields = (
        'log_id', 'action', 'target_username', 'target_type',
        'performed_by', 'timestamp', 'details',
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.groups.filter(name='Admin').exists():
            return qs
        return qs.none()

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(
            name__in=['Admin', 'Editor', 'Viewer', 'Approver']
        ).exists()

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_staff

    def has_module_permission(self, request):
        return _is_admin_or_super(request.user)


# ============================================================
# USER VERIFICATION ADMIN
# ============================================================

@admin.register(UserVerification)
class UserVerificationAdmin(admin.ModelAdmin):
    list_display = (
        'get_username', 'is_totp_enabled',
        'failed_attempts', 'timeout_until', 'created_at',
    )
    list_filter = ('is_totp_enabled',)
    search_fields = ('account__username',)
    readonly_fields = (
        'account', 'is_totp_enabled', 'failed_attempts',
        'timeout_until', 'created_at',
    )

    fieldsets = (
        (None, {
            'fields': (
                'account', 'is_totp_enabled',
                'failed_attempts', 'timeout_until', 'created_at',
            ),
        }),
    )

    def get_username(self, obj):
        return obj.account.username
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'account__username'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('account')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return _is_admin_or_super(request.user)

    def has_view_permission(self, request, obj=None):
        return _is_admin_or_super(request.user)

    def has_module_permission(self, request):
        return _is_admin_or_super(request.user)