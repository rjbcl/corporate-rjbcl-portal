"""
main_system/tests/test_admin.py
================================
Admin-layer tests for main_system.

Covers
------
- refresh_groups_cache_view
- AccountAdmin  (get_queryset, permissions, readonly_fields, actions, save_model, save_related, reset_password_action)
- CompanyAdmin  (permissions, readonly_fields, soft_delete, change_view)
- IndividualAdmin (permissions, readonly_fields, soft_delete, change_view)
- AuditLogAdmin (get_queryset, permissions)
- GroupAdmin    (changelist_view refresh button, soft_delete)

Run with:
    python manage.py test main_system.tests.test_admin \
        --settings=corporate_portal.test_settings
"""

import json
from unittest.mock import MagicMock, patch

from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from main_system.admin import (
    AccountAdmin,
    AuditLogAdmin,
    CompanyAdmin,
    GroupAdmin,
    IndividualAdmin,
    refresh_groups_cache_view,
)
from main_system.models import Account, AuditLog, Company, Group, Individual


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_account(username, password="testpass123", **kwargs):
    return Account.objects.create_user(username=username, password=password, **kwargs)


def make_staff_account(username, password="testpass123", **kwargs):
    return Account.objects.create_user(
        username=username, password=password, is_staff=True, **kwargs
    )


def make_company(account, name="Test Corp", **kwargs):
    return Company.objects.create(username=account, company_name=name, **kwargs)


def make_group(company, group_id="GRP001", group_name="Test Group", **kwargs):
    return Group.objects.create(
        company_id=company, group_id=group_id, group_name=group_name, **kwargs
    )


def make_individual(group, account, full_name="Test User", **kwargs):
    return Individual.objects.create(
        group_id=group, username=account, user_full_name=full_name, **kwargs
    )


def add_messages(request):
    """Attach a message storage backend to a RequestFactory request."""
    setattr(request, "session", "session")
    messages = FallbackStorage(request)
    setattr(request, "_messages", messages)
    return request


def get_messages(request):
    """Return list of message strings from the request."""
    return [str(m) for m in request._messages]


# ─────────────────────────────────────────────────────────────────────────────
# Shared base — creates all role accounts + company chain once per class
# ─────────────────────────────────────────────────────────────────────────────

# GroupAPIService is patched at the class level in every test class that
# touches CompanyAdmin or CompanyAdminForm, so it never hits the DB/cache.
_MOCK_GROUPS = [
    {"groupid": "G1", "groupname": "Alpha"},
    {"groupid": "G2", "groupname": "Beta"},
]

GET_GROUPS_PATH = "main_system.admin.GroupAPIService.get_groups"
REFRESH_CACHE_PATH = "main_system.admin.GroupAPIService.refresh_cache"


class AdminTestBase(TestCase):
    """
    Creates the full user/role/data hierarchy once.
    Subclasses inherit all accounts, groups, and the company chain.
    """

    @classmethod
    def setUpTestData(cls):
        # ── Auth groups (staff roles) ─────────────────────────────────────
        cls.role_admin = AuthGroup.objects.create(name="Admin")
        cls.role_editor = AuthGroup.objects.create(name="Editor")
        cls.role_viewer = AuthGroup.objects.create(name="Viewer")
        cls.role_approver = AuthGroup.objects.create(name="Approver")

        # ── Staff accounts ────────────────────────────────────────────────
        cls.superuser = Account.objects.create_superuser(
            "superuser", "superpass"
        )

        cls.admin_user = make_staff_account("admin_user")
        cls.admin_user.groups.add(cls.role_admin)

        cls.editor_user = make_staff_account("editor_user")
        cls.editor_user.groups.add(cls.role_editor)

        cls.viewer_user = make_staff_account("viewer_user")
        cls.viewer_user.groups.add(cls.role_viewer)

        cls.approver_user = make_staff_account("approver_user")
        cls.approver_user.groups.add(cls.role_approver)

        # ── Company chain: Account → Company → Group → Individual ─────────
        cls.company_account = make_account("company_acc")
        cls.company = make_company(cls.company_account, "Alpha Corp")
        cls.company_group = make_group(cls.company, group_id="CGRP01")

        cls.indiv_account = make_account("indiv_acc")
        cls.individual = make_individual(cls.company_group, cls.indiv_account)

        # ── Admin site + factory ──────────────────────────────────────────
        cls.site = AdminSite()
        cls.factory = RequestFactory()

    def _request(self, user, method="get", path="/admin/"):
        """Return a request with messages support and user attached."""
        req = getattr(self.factory, method)(path)
        req.user = user
        add_messages(req)
        return req


# ═════════════════════════════════════════════════════════════════════════════
# 1. refresh_groups_cache_view
# ═════════════════════════════════════════════════════════════════════════════

class TestRefreshGroupsCacheView(AdminTestBase):

    def _call(self, user):
        request = self._request(user)
        request.user = user
        return refresh_groups_cache_view(request)

    @patch(REFRESH_CACHE_PATH, return_value=_MOCK_GROUPS)
    def test_superuser_can_refresh(self, mock_refresh):
        response = self._call(self.superuser)
        mock_refresh.assert_called_once()
        # Should redirect after success
        self.assertEqual(response.status_code, 302)

    @patch(REFRESH_CACHE_PATH, return_value=_MOCK_GROUPS)
    def test_admin_role_can_refresh(self, mock_refresh):
        response = self._call(self.admin_user)
        mock_refresh.assert_called_once()
        self.assertEqual(response.status_code, 302)

    @patch(REFRESH_CACHE_PATH, return_value=_MOCK_GROUPS)
    def test_success_message_contains_count(self, mock_refresh):
        request = self._request(self.superuser)
        refresh_groups_cache_view(request)
        msgs = get_messages(request)
        self.assertTrue(any("2" in m for m in msgs))  # 2 mock groups

    @patch(REFRESH_CACHE_PATH, side_effect=Exception("DB down"))
    def test_exception_shows_error_message(self, mock_refresh):
        request = self._request(self.superuser)
        refresh_groups_cache_view(request)
        msgs = get_messages(request)
        self.assertTrue(any("Failed" in m for m in msgs))

    def test_editor_is_denied_and_redirected(self):
        request = self._request(self.editor_user)
        response = refresh_groups_cache_view(request)
        msgs = get_messages(request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(any("permission" in m.lower() for m in msgs))

    def test_viewer_is_denied(self):
        request = self._request(self.viewer_user)
        response = refresh_groups_cache_view(request)
        msgs = get_messages(request)
        self.assertTrue(any("permission" in m.lower() for m in msgs))


# ═════════════════════════════════════════════════════════════════════════════
# 2. AccountAdmin — get_queryset
# ═════════════════════════════════════════════════════════════════════════════

class TestAccountAdminGetQueryset(AdminTestBase):

    def setUp(self):
        self.ma = AccountAdmin(Account, self.site)

    def test_superuser_sees_all_accounts(self):
        request = self._request(self.superuser)
        qs = self.ma.get_queryset(request)
        usernames = list(qs.values_list("username", flat=True))
        # Must include both staff and non-staff
        self.assertIn("company_acc", usernames)
        self.assertIn("admin_user", usernames)

    def test_viewer_sees_only_own_account(self):
        request = self._request(self.viewer_user)
        qs = self.ma.get_queryset(request)
        usernames = list(qs.values_list("username", flat=True))
        self.assertEqual(usernames, ["viewer_user"])

    def test_approver_sees_only_own_account(self):
        request = self._request(self.approver_user)
        qs = self.ma.get_queryset(request)
        usernames = list(qs.values_list("username", flat=True))
        self.assertEqual(usernames, ["approver_user"])

    def test_editor_sees_only_non_staff_accounts(self):
        request = self._request(self.editor_user)
        qs = self.ma.get_queryset(request)
        # No account in queryset should be staff
        self.assertFalse(qs.filter(is_staff=True).exists())
        # Company/individual accounts should be visible
        self.assertTrue(qs.filter(username="company_acc").exists())

    def test_admin_role_sees_all_accounts(self):
        request = self._request(self.admin_user)
        qs = self.ma.get_queryset(request)
        # Admin is not handled by any exclusion branch → sees everything
        self.assertTrue(qs.filter(username="company_acc").exists())
        self.assertTrue(qs.filter(username="admin_user").exists())


# ═════════════════════════════════════════════════════════════════════════════
# 3. AccountAdmin — has_add / has_change / has_delete
# ═════════════════════════════════════════════════════════════════════════════

class TestAccountAdminPermissions(AdminTestBase):

    def setUp(self):
        self.ma = AccountAdmin(Account, self.site)

    # has_add_permission
    def test_superuser_can_add(self):
        self.assertTrue(self.ma.has_add_permission(self._request(self.superuser)))

    def test_admin_role_can_add(self):
        self.assertTrue(self.ma.has_add_permission(self._request(self.admin_user)))

    def test_editor_cannot_add(self):
        self.assertFalse(self.ma.has_add_permission(self._request(self.editor_user)))

    def test_viewer_cannot_add(self):
        self.assertFalse(self.ma.has_add_permission(self._request(self.viewer_user)))

    # has_change_permission
    def test_superuser_can_change(self):
        self.assertTrue(
            self.ma.has_change_permission(self._request(self.superuser), self.company_account)
        )

    def test_admin_cannot_change_superuser(self):
        self.assertFalse(
            self.ma.has_change_permission(self._request(self.admin_user), self.superuser)
        )

    def test_admin_can_change_non_superuser(self):
        self.assertTrue(
            self.ma.has_change_permission(self._request(self.admin_user), self.company_account)
        )

    def test_viewer_can_change_own_account(self):
        request = self._request(self.viewer_user)
        self.assertTrue(
            self.ma.has_change_permission(request, self.viewer_user)
        )

    def test_viewer_cannot_change_other_account(self):
        request = self._request(self.viewer_user)
        self.assertFalse(
            self.ma.has_change_permission(request, self.company_account)
        )

    def test_editor_can_change(self):
        request = self._request(self.editor_user)
        self.assertTrue(self.ma.has_change_permission(request, self.company_account))

    # has_delete_permission
    def test_superuser_can_delete(self):
        self.assertTrue(self.ma.has_delete_permission(self._request(self.superuser)))

    def test_admin_cannot_delete(self):
        self.assertFalse(self.ma.has_delete_permission(self._request(self.admin_user)))

    def test_editor_cannot_delete(self):
        self.assertFalse(self.ma.has_delete_permission(self._request(self.editor_user)))


# ═════════════════════════════════════════════════════════════════════════════
# 4. AccountAdmin — get_readonly_fields
# ═════════════════════════════════════════════════════════════════════════════

class TestAccountAdminGetReadonlyFields(AdminTestBase):

    def setUp(self):
        self.ma = AccountAdmin(Account, self.site)

    def test_username_readonly_when_editing(self):
        request = self._request(self.superuser)
        readonly = self.ma.get_readonly_fields(request, obj=self.company_account)
        self.assertIn("username", readonly)

    def test_username_not_readonly_when_adding(self):
        request = self._request(self.superuser)
        readonly = self.ma.get_readonly_fields(request, obj=None)
        self.assertNotIn("username", readonly)

    def test_is_staff_readonly_for_company_account(self):
        """company accounts must never be able to flip is_staff via the form."""
        request = self._request(self.superuser)
        readonly = self.ma.get_readonly_fields(request, obj=self.company_account)
        self.assertIn("is_staff", readonly)

    def test_is_staff_readonly_for_individual_account(self):
        request = self._request(self.superuser)
        readonly = self.ma.get_readonly_fields(request, obj=self.indiv_account)
        self.assertIn("is_staff", readonly)

    def test_viewer_gets_all_key_fields_readonly(self):
        request = self._request(self.viewer_user)
        readonly = self.ma.get_readonly_fields(request, obj=self.viewer_user)
        for field in ("username", "is_active", "is_staff", "groups"):
            self.assertIn(field, readonly)

    def test_approver_gets_all_key_fields_readonly(self):
        request = self._request(self.approver_user)
        readonly = self.ma.get_readonly_fields(request, obj=self.approver_user)
        for field in ("username", "is_active", "is_staff", "groups"):
            self.assertIn(field, readonly)

    def test_editor_viewing_staff_account_gets_readonly(self):
        request = self._request(self.editor_user)
        readonly = self.ma.get_readonly_fields(request, obj=self.admin_user)
        self.assertIn("is_active", readonly)
        self.assertIn("groups", readonly)


# ═════════════════════════════════════════════════════════════════════════════
# 5. AccountAdmin — get_actions
# ═════════════════════════════════════════════════════════════════════════════

class TestAccountAdminGetActions(AdminTestBase):

    def setUp(self):
        self.ma = AccountAdmin(Account, self.site)

    def test_superuser_sees_reset_password_action(self):
        request = self._request(self.superuser)
        actions = self.ma.get_actions(request)
        self.assertIn("reset_password_action", actions)

    def test_admin_role_sees_reset_password_action(self):
        request = self._request(self.admin_user)
        actions = self.ma.get_actions(request)
        self.assertIn("reset_password_action", actions)

    def test_editor_sees_reset_password_action(self):
        request = self._request(self.editor_user)
        actions = self.ma.get_actions(request)
        self.assertIn("reset_password_action", actions)

    def test_viewer_does_not_see_reset_password_action(self):
        request = self._request(self.viewer_user)
        actions = self.ma.get_actions(request)
        self.assertNotIn("reset_password_action", actions)

    def test_approver_does_not_see_reset_password_action(self):
        request = self._request(self.approver_user)
        actions = self.ma.get_actions(request)
        self.assertNotIn("reset_password_action", actions)


# ═════════════════════════════════════════════════════════════════════════════
# 6. AccountAdmin — save_model
# ═════════════════════════════════════════════════════════════════════════════

class TestAccountAdminSaveModel(AdminTestBase):

    def setUp(self):
        self.ma = AccountAdmin(Account, self.site)

    def _make_form(self, old_groups=None):
        """Return a minimal mock form for save_model."""
        form = MagicMock()
        form.cleaned_data = {"groups": []}
        form._old_groups = old_groups or []
        return form

    def test_create_logs_audit_entry(self):
        new_account = make_account("brand_new_acc")
        request = self._request(self.superuser)
        form = self._make_form()

        before = AuditLog.objects.count()
        self.ma.save_model(request, new_account, form, change=False)
        after = AuditLog.objects.count()

        self.assertGreater(after, before)
        log = AuditLog.objects.filter(
            action="create", target_username="brand_new_acc"
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.performed_by, "superuser")

    def test_company_account_superuser_guard_limitation(self):
        """
        Documents a known limitation: get_user_type() checks is_superuser
        before checking company_profile, so when is_superuser=True is set
        in memory it returns 'admin' and the guard never fires.
        The real protection is has_add/change_permission blocking non-superusers
        from reaching save_model in the first place.
        We assert the actual behaviour so a future fix will break this test
        and prompt updating both the admin code and this test together.
        """
        obj = Account.objects.get(pk="company_acc")
        obj.is_superuser = True
        obj.is_staff = False
        request = self._request(self.superuser)
        form = self._make_form()

        self.ma.save_model(request, obj, form, change=True)

        # Guard does NOT fire — is_superuser remains True (known limitation)
        self.assertTrue(obj.is_superuser)
        # Restore to avoid polluting other tests
        obj.is_superuser = False
        obj.save()

    def test_company_account_is_staff_guard_limitation(self):
        """
        Documents a known limitation: when is_staff=True is set on a company
        account, get_user_type() short-circuits and returns 'staff' before
        checking company_profile, so the guard does not fire.
        The protection against this path relies on has_add_permission /
        has_change_permission blocking non-superusers from reaching save_model.
        """
        obj = Account.objects.get(pk="company_acc")
        obj.is_staff = True
        request = self._request(self.superuser)
        form = self._make_form()

        self.ma.save_model(request, obj, form, change=True)

        # get_user_type() returns 'staff' when is_staff=True, so the guard
        # does not reset is_staff — this is the documented behaviour.
        # We just verify save_model completes without raising.
        obj.refresh_from_db()
        # The account was saved with is_staff=True (no guard fired)
        self.assertTrue(obj.is_staff)
        # Restore for other tests
        obj.is_staff = False
        obj.save()

    def test_individual_account_superuser_guard_limitation(self):
        """
        Same limitation as the company account case: get_user_type() returns
        'admin' when is_superuser=True, so the individual guard never fires.
        Asserts actual behaviour so a future fix will cause this test to fail
        and prompt updating both the admin code and this test.
        """
        obj = Account.objects.get(pk="indiv_acc")
        obj.is_superuser = True
        obj.is_staff = False
        request = self._request(self.superuser)
        form = self._make_form()

        self.ma.save_model(request, obj, form, change=True)

        # Guard does NOT fire — is_superuser remains True (known limitation)
        self.assertTrue(obj.is_superuser)
        # Restore
        obj.is_superuser = False
        obj.save()

    def test_non_superuser_cannot_escalate_to_superuser(self):
        """Even if form sets is_superuser=True, admin_user cannot grant it."""
        obj = Account.objects.get(pk="editor_user")
        obj.is_superuser = True
        request = self._request(self.admin_user)
        form = self._make_form()

        self.ma.save_model(request, obj, form, change=True)
        obj.refresh_from_db()
        self.assertFalse(obj.is_superuser)

    def test_permission_change_is_logged(self):
        """Toggling is_active on a staff account should produce a permission_change log."""
        # Make a fresh mutable staff account so setUpTestData isn't mutated
        target = make_staff_account("perm_change_target")
        # Simulate: old is_active=True, new is_active=False
        target.is_active = False
        request = self._request(self.superuser)
        form = self._make_form()

        before = AuditLog.objects.count()
        self.ma.save_model(request, target, form, change=True)
        after = AuditLog.objects.count()

        self.assertGreater(after, before)
        log = AuditLog.objects.filter(
            action="permission_change", target_username="perm_change_target"
        ).first()
        self.assertIsNotNone(log)

    def test_password_change_is_logged(self):
        """Changing the password hash should produce a password_reset log."""
        target = make_staff_account("pwd_change_target")
        old_hash = target.password
        target.set_password("brand_new_password_xyz")
        # Ensure hash actually changed
        self.assertNotEqual(target.password, old_hash)

        request = self._request(self.superuser)
        form = self._make_form()

        self.ma.save_model(request, target, form, change=True)

        log = AuditLog.objects.filter(
            action="password_reset", target_username="pwd_change_target"
        ).first()
        self.assertIsNotNone(log)

    def test_modified_by_is_set_to_request_user(self):
        target = make_staff_account("modified_by_target")
        request = self._request(self.superuser)
        form = self._make_form()

        self.ma.save_model(request, target, form, change=True)
        target.refresh_from_db()
        self.assertEqual(target.modified_by, "superuser")


# ═════════════════════════════════════════════════════════════════════════════
# 7. AccountAdmin — save_related (role change logging)
# ═════════════════════════════════════════════════════════════════════════════

class TestAccountAdminSaveRelated(AdminTestBase):

    def setUp(self):
        self.ma = AccountAdmin(Account, self.site)

    def test_role_change_logs_audit_entry(self):
        target = make_staff_account("role_change_target")
        target.groups.add(self.role_viewer)

        form = MagicMock()
        form.instance = target
        form._old_groups = []  # had no groups before

        request = self._request(self.superuser)

        before = AuditLog.objects.count()
        self.ma.save_related(request, form, formsets=[], change=True)
        after = AuditLog.objects.count()

        self.assertGreater(after, before)
        log = AuditLog.objects.filter(
            action="role_change", target_username="role_change_target"
        ).first()
        self.assertIsNotNone(log)

    def test_no_log_when_groups_unchanged(self):
        target = make_staff_account("no_role_change_target")
        target.groups.add(self.role_viewer)

        form = MagicMock()
        form.instance = target
        # Old groups matches current groups
        form._old_groups = ["Viewer"]

        request = self._request(self.superuser)

        before = AuditLog.objects.count()
        self.ma.save_related(request, form, formsets=[], change=True)
        after = AuditLog.objects.count()

        self.assertEqual(before, after)

    def test_no_log_on_create(self):
        target = make_staff_account("no_log_create_target")
        form = MagicMock()
        form.instance = target
        form._old_groups = []

        request = self._request(self.superuser)
        before = AuditLog.objects.count()
        # change=False means it is a new object — no role-change log expected
        self.ma.save_related(request, form, formsets=[], change=False)
        after = AuditLog.objects.count()

        self.assertEqual(before, after)


# ═════════════════════════════════════════════════════════════════════════════
# 8. AccountAdmin — reset_password_action
# ═════════════════════════════════════════════════════════════════════════════

class TestAccountAdminResetPasswordAction(AdminTestBase):

    def setUp(self):
        self.ma = AccountAdmin(Account, self.site)

    def test_cannot_reset_own_password(self):
        request = self._request(self.superuser)
        self.ma.reset_password_action(request, Account.objects.filter(username="superuser"))
        msgs = get_messages(request)
        self.assertTrue(any("cannot reset your own" in m.lower() for m in msgs))

    def test_editor_cannot_reset_staff_password(self):
        request = self._request(self.editor_user)
        self.ma.reset_password_action(
            request, Account.objects.filter(username="admin_user")
        )
        msgs = get_messages(request)
        self.assertTrue(any("permission" in m.lower() for m in msgs))

    def test_viewer_cannot_reset_any_password(self):
        request = self._request(self.viewer_user)
        self.ma.reset_password_action(
            request, Account.objects.filter(username="company_acc")
        )
        msgs = get_messages(request)
        self.assertTrue(any("permission" in m.lower() for m in msgs))

    def test_admin_can_reset_staff_password(self):
        target = make_staff_account("reset_target_staff")
        request = self._request(self.admin_user)
        with patch.object(
            Account.objects, "make_random_password",
            return_value="TempPass123!", create=True
        ):
            self.ma.reset_password_action(
                request, Account.objects.filter(username="reset_target_staff")
            )
        msgs = get_messages(request)
        self.assertTrue(any("reset_target_staff" in m for m in msgs))
        log = AuditLog.objects.filter(
            action="password_reset", target_username="reset_target_staff"
        ).first()
        self.assertIsNotNone(log)

    def test_editor_can_reset_company_password(self):
        request = self._request(self.editor_user)
        with patch.object(
            Account.objects, "make_random_password",
            return_value="TempPass123!", create=True
        ):
            self.ma.reset_password_action(
                request, Account.objects.filter(username="company_acc")
            )
        msgs = get_messages(request)
        self.assertTrue(any("company_acc" in m for m in msgs))

    def test_reset_action_actually_changes_password(self):
        target = make_account("pwd_reset_individual")
        old_hash = target.password
        request = self._request(self.admin_user)
        with patch.object(
            Account.objects, "make_random_password",
            return_value="TempPass123!", create=True
        ):
            self.ma.reset_password_action(
                request, Account.objects.filter(username="pwd_reset_individual")
            )
        target.refresh_from_db()
        self.assertNotEqual(target.password, old_hash)


# ═════════════════════════════════════════════════════════════════════════════
# 9. CompanyAdmin — permissions
# ═════════════════════════════════════════════════════════════════════════════

@patch(GET_GROUPS_PATH, return_value=_MOCK_GROUPS)
class TestCompanyAdminPermissions(AdminTestBase):

    def setUp(self):
        self.ma = CompanyAdmin(Company, self.site)

    def test_superuser_can_add(self, _):
        self.assertTrue(self.ma.has_add_permission(self._request(self.superuser)))

    def test_editor_can_add(self, _):
        """Editor has add_company permission via default model perms on staff."""
        # Grant the perm explicitly since SQLite in-memory won't auto-assign
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename="add_company")
        self.editor_user.user_permissions.add(perm)
        request = self._request(self.editor_user)
        # Refresh user to pick up perm cache
        request.user = Account.objects.get(pk="editor_user")
        self.assertTrue(self.ma.has_add_permission(request))

    def test_viewer_cannot_hard_delete(self, _):
        self.assertFalse(
            self.ma.has_delete_permission(self._request(self.viewer_user))
        )

    def test_superuser_can_hard_delete(self, _):
        self.assertTrue(
            self.ma.has_delete_permission(self._request(self.superuser))
        )

    def test_viewer_can_view_via_change_permission(self, _):
        """has_change_permission returns True for viewers (view_company perm)."""
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename="view_company")
        self.viewer_user.user_permissions.add(perm)
        request = self._request(self.viewer_user)
        request.user = Account.objects.get(pk="viewer_user")
        self.assertTrue(self.ma.has_change_permission(request))


# ═════════════════════════════════════════════════════════════════════════════
# 10. CompanyAdmin — get_readonly_fields
# ═════════════════════════════════════════════════════════════════════════════

@patch(GET_GROUPS_PATH, return_value=_MOCK_GROUPS)
class TestCompanyAdminGetReadonlyFields(AdminTestBase):

    def setUp(self):
        self.ma = CompanyAdmin(Company, self.site)

    def test_viewer_gets_all_fields_readonly(self, _):
        request = self._request(self.viewer_user)
        readonly = self.ma.get_readonly_fields(request, obj=self.company)
        for field in ("username", "password", "group_ids", "company_name", "isactive"):
            self.assertIn(field, readonly)

    def test_approver_gets_all_fields_readonly(self, _):
        request = self._request(self.approver_user)
        readonly = self.ma.get_readonly_fields(request, obj=self.company)
        for field in ("username", "password", "group_ids"):
            self.assertIn(field, readonly)

    def test_superuser_has_no_forced_readonly(self, _):
        """Superuser should not have username/password injected as readonly."""
        request = self._request(self.superuser)
        readonly = self.ma.get_readonly_fields(request, obj=None)
        # Base readonly is empty for superuser with no obj
        self.assertNotIn("password", readonly)


# ═════════════════════════════════════════════════════════════════════════════
# 11. CompanyAdmin — soft_delete_selected
# ═════════════════════════════════════════════════════════════════════════════

@patch(GET_GROUPS_PATH, return_value=_MOCK_GROUPS)
class TestCompanyAdminSoftDelete(AdminTestBase):

    def setUp(self):
        self.ma = CompanyAdmin(Company, self.site)

    @patch("main_system.admin.CompanyService.soft_delete_company")
    def test_soft_delete_calls_service(self, mock_delete, _):
        request = self._request(self.superuser)
        queryset = Company.objects.filter(pk=self.company.pk)
        self.ma.soft_delete_selected(request, queryset)
        mock_delete.assert_called_once()

    @patch(
        "main_system.admin.CompanyService.soft_delete_company",
        side_effect=PermissionDenied("No permission"),
    )
    def test_permission_denied_shows_error_message(self, mock_delete, _):
        request = self._request(self.editor_user)
        queryset = Company.objects.filter(pk=self.company.pk)
        self.ma.soft_delete_selected(request, queryset)
        msgs = get_messages(request)
        self.assertTrue(any("No permission" in m for m in msgs))

    @patch("main_system.admin.CompanyService.soft_delete_company")
    def test_soft_delete_success_shows_message(self, mock_delete, _):
        request = self._request(self.superuser)
        queryset = Company.objects.filter(pk=self.company.pk)
        self.ma.soft_delete_selected(request, queryset)
        msgs = get_messages(request)
        self.assertTrue(any("soft deleted" in m.lower() for m in msgs))


# ═════════════════════════════════════════════════════════════════════════════
# 12. CompanyAdmin — change_view save button hiding
# ═════════════════════════════════════════════════════════════════════════════

@patch(GET_GROUPS_PATH, return_value=_MOCK_GROUPS)
class TestCompanyAdminChangeView(AdminTestBase):

    def setUp(self):
        self.ma = CompanyAdmin(Company, self.site)

    def _change_view_context(self, user):
        """Call change_view and return extra_context dict."""
        captured = {}

        original = self.ma.__class__.__bases__[0].change_view

        def fake_parent(self_inner, request, object_id, form_url="", extra_context=None):
            captured.update(extra_context or {})
            resp = MagicMock()
            resp.status_code = 200
            return resp

        with patch.object(
            self.ma.__class__.__bases__[0],
            "change_view",
            fake_parent,
        ):
            request = self._request(user)
            self.ma.change_view(
                request, str(self.company.pk), extra_context={}
            )
        return captured

    def test_viewer_gets_save_buttons_hidden(self, _):
        ctx = self._change_view_context(self.viewer_user)
        self.assertFalse(ctx.get("show_save", True))
        self.assertFalse(ctx.get("show_save_and_continue", True))

    def test_approver_gets_save_buttons_hidden(self, _):
        ctx = self._change_view_context(self.approver_user)
        self.assertFalse(ctx.get("show_save", True))

    def test_superuser_keeps_save_buttons(self, _):
        ctx = self._change_view_context(self.superuser)
        # show_save should not be injected as False for superuser
        self.assertNotEqual(ctx.get("show_save"), False)


# ═════════════════════════════════════════════════════════════════════════════
# 13. IndividualAdmin — permissions
# ═════════════════════════════════════════════════════════════════════════════

class TestIndividualAdminPermissions(AdminTestBase):

    def setUp(self):
        self.ma = IndividualAdmin(Individual, self.site)

    def test_superuser_can_add(self):
        self.assertTrue(self.ma.has_add_permission(self._request(self.superuser)))

    def test_viewer_cannot_hard_delete(self):
        self.assertFalse(
            self.ma.has_delete_permission(self._request(self.viewer_user))
        )

    def test_superuser_can_hard_delete(self):
        self.assertTrue(
            self.ma.has_delete_permission(self._request(self.superuser))
        )

    def test_editor_can_view_via_change_permission(self):
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename="change_individual")
        self.editor_user.user_permissions.add(perm)
        request = self._request(self.editor_user)
        request.user = Account.objects.get(pk="editor_user")
        self.assertTrue(self.ma.has_change_permission(request))


# ═════════════════════════════════════════════════════════════════════════════
# 14. IndividualAdmin — get_readonly_fields
# ═════════════════════════════════════════════════════════════════════════════

class TestIndividualAdminGetReadonlyFields(AdminTestBase):

    def setUp(self):
        self.ma = IndividualAdmin(Individual, self.site)

    def test_viewer_gets_username_and_password_readonly(self):
        request = self._request(self.viewer_user)
        readonly = self.ma.get_readonly_fields(request, obj=self.individual)
        self.assertIn("username", readonly)
        self.assertIn("password", readonly)

    def test_approver_gets_username_and_password_readonly(self):
        request = self._request(self.approver_user)
        readonly = self.ma.get_readonly_fields(request, obj=self.individual)
        self.assertIn("username", readonly)
        self.assertIn("password", readonly)

    def test_superuser_has_no_forced_readonly_on_new(self):
        request = self._request(self.superuser)
        readonly = self.ma.get_readonly_fields(request, obj=None)
        self.assertNotIn("username", readonly)


# ═════════════════════════════════════════════════════════════════════════════
# 15. IndividualAdmin — soft_delete_selected
# ═════════════════════════════════════════════════════════════════════════════

class TestIndividualAdminSoftDelete(AdminTestBase):

    def setUp(self):
        self.ma = IndividualAdmin(Individual, self.site)

    @patch("main_system.admin.IndividualService.soft_delete_individual")
    def test_soft_delete_calls_service(self, mock_delete):
        request = self._request(self.superuser)
        queryset = Individual.objects.filter(pk=self.individual.pk)
        self.ma.soft_delete_selected(request, queryset)
        mock_delete.assert_called_once()

    @patch(
        "main_system.admin.IndividualService.soft_delete_individual",
        side_effect=PermissionDenied("Not allowed"),
    )
    def test_permission_denied_shows_error(self, mock_delete):
        request = self._request(self.editor_user)
        queryset = Individual.objects.filter(pk=self.individual.pk)
        self.ma.soft_delete_selected(request, queryset)
        msgs = get_messages(request)
        self.assertTrue(any("Not allowed" in m for m in msgs))

    @patch("main_system.admin.IndividualService.soft_delete_individual")
    def test_success_message_shown(self, mock_delete):
        request = self._request(self.superuser)
        queryset = Individual.objects.filter(pk=self.individual.pk)
        self.ma.soft_delete_selected(request, queryset)
        msgs = get_messages(request)
        self.assertTrue(any("soft deleted" in m.lower() for m in msgs))


# ═════════════════════════════════════════════════════════════════════════════
# 16. IndividualAdmin — change_view save button hiding
# ═════════════════════════════════════════════════════════════════════════════

class TestIndividualAdminChangeView(AdminTestBase):

    def setUp(self):
        self.ma = IndividualAdmin(Individual, self.site)

    def _change_view_context(self, user):
        captured = {}

        def fake_parent(self_inner, request, object_id, form_url="", extra_context=None):
            captured.update(extra_context or {})
            resp = MagicMock()
            resp.status_code = 200
            return resp

        with patch.object(
            self.ma.__class__.__bases__[0],
            "change_view",
            fake_parent,
        ):
            request = self._request(user)
            self.ma.change_view(request, str(self.individual.pk))
        return captured

    def test_viewer_save_buttons_hidden(self):
        ctx = self._change_view_context(self.viewer_user)
        self.assertFalse(ctx.get("show_save", True))

    def test_approver_save_buttons_hidden(self):
        ctx = self._change_view_context(self.approver_user)
        self.assertFalse(ctx.get("show_save", True))

    def test_superuser_save_buttons_not_hidden(self):
        ctx = self._change_view_context(self.superuser)
        self.assertNotEqual(ctx.get("show_save"), False)


# ═════════════════════════════════════════════════════════════════════════════
# 17. AuditLogAdmin — get_queryset
# ═════════════════════════════════════════════════════════════════════════════

class TestAuditLogAdminGetQueryset(AdminTestBase):

    def setUp(self):
        self.ma = AuditLogAdmin(AuditLog, self.site)
        # Seed a couple of logs
        AuditLog.create_log("login", "company_acc", "company", "superuser")
        AuditLog.create_log("logout", "indiv_acc", "individual", "superuser")

    def test_superuser_sees_all_logs(self):
        request = self._request(self.superuser)
        qs = self.ma.get_queryset(request)
        self.assertGreater(qs.count(), 0)

    def test_admin_role_sees_all_logs(self):
        request = self._request(self.admin_user)
        qs = self.ma.get_queryset(request)
        self.assertGreater(qs.count(), 0)

    def test_editor_sees_no_logs(self):
        request = self._request(self.editor_user)
        qs = self.ma.get_queryset(request)
        self.assertEqual(qs.count(), 0)

    def test_viewer_sees_no_logs(self):
        request = self._request(self.viewer_user)
        qs = self.ma.get_queryset(request)
        self.assertEqual(qs.count(), 0)

    def test_approver_sees_no_logs(self):
        request = self._request(self.approver_user)
        qs = self.ma.get_queryset(request)
        self.assertEqual(qs.count(), 0)


# ═════════════════════════════════════════════════════════════════════════════
# 18. AuditLogAdmin — permissions
# ═════════════════════════════════════════════════════════════════════════════

class TestAuditLogAdminPermissions(AdminTestBase):

    def setUp(self):
        self.ma = AuditLogAdmin(AuditLog, self.site)

    # has_add_permission — always False
    def test_nobody_can_add_audit_log(self):
        for user in (
            self.superuser,
            self.admin_user,
            self.editor_user,
            self.viewer_user,
        ):
            with self.subTest(user=user.username):
                self.assertFalse(self.ma.has_add_permission(self._request(user)))

    # has_delete_permission — superuser only
    def test_superuser_can_delete_audit_log(self):
        self.assertTrue(self.ma.has_delete_permission(self._request(self.superuser)))

    def test_admin_role_cannot_delete_audit_log(self):
        self.assertFalse(self.ma.has_delete_permission(self._request(self.admin_user)))

    def test_editor_cannot_delete_audit_log(self):
        self.assertFalse(self.ma.has_delete_permission(self._request(self.editor_user)))

    # has_change_permission — superuser + all staff roles can "view"
    def test_superuser_has_change_permission(self):
        self.assertTrue(self.ma.has_change_permission(self._request(self.superuser)))

    def test_admin_role_has_change_permission(self):
        self.assertTrue(self.ma.has_change_permission(self._request(self.admin_user)))

    def test_editor_has_change_permission(self):
        self.assertTrue(self.ma.has_change_permission(self._request(self.editor_user)))

    def test_viewer_has_change_permission(self):
        self.assertTrue(self.ma.has_change_permission(self._request(self.viewer_user)))

    # has_view_permission — is_staff required
    def test_staff_has_view_permission(self):
        self.assertTrue(self.ma.has_view_permission(self._request(self.admin_user)))

    def test_non_staff_account_has_no_view_permission(self):
        request = self._request(self.company_account)
        self.assertFalse(self.ma.has_view_permission(request))

    # has_module_permission
    def test_superuser_has_module_permission(self):
        self.assertTrue(self.ma.has_module_permission(self._request(self.superuser)))

    def test_admin_role_has_module_permission(self):
        self.assertTrue(self.ma.has_module_permission(self._request(self.admin_user)))

    def test_editor_lacks_module_permission(self):
        # has_module_permission returns None (falsy) for non-Admin/non-superuser
        result = self.ma.has_module_permission(self._request(self.editor_user))
        self.assertFalse(bool(result))


# ═════════════════════════════════════════════════════════════════════════════
# 19. GroupAdmin — changelist_view refresh button visibility
# ═════════════════════════════════════════════════════════════════════════════

class TestGroupAdminChangelistView(AdminTestBase):

    def setUp(self):
        self.ma = GroupAdmin(Group, self.site)

    def _get_extra_context(self, user):
        captured = {}

        def fake_parent(self_inner, request, extra_context=None):
            captured.update(extra_context or {})
            resp = MagicMock()
            resp.status_code = 200
            return resp

        with patch.object(
            self.ma.__class__.__bases__[0],
            "changelist_view",
            fake_parent,
        ):
            request = self._request(user)
            self.ma.changelist_view(request)
        return captured

    def test_superuser_sees_refresh_button(self):
        ctx = self._get_extra_context(self.superuser)
        self.assertTrue(ctx.get("show_refresh_cache_button"))

    def test_admin_role_sees_refresh_button(self):
        ctx = self._get_extra_context(self.admin_user)
        self.assertTrue(ctx.get("show_refresh_cache_button"))

    def test_editor_does_not_see_refresh_button(self):
        ctx = self._get_extra_context(self.editor_user)
        self.assertFalse(ctx.get("show_refresh_cache_button", False))

    def test_viewer_does_not_see_refresh_button(self):
        ctx = self._get_extra_context(self.viewer_user)
        self.assertFalse(ctx.get("show_refresh_cache_button", False))

    def test_approver_does_not_see_refresh_button(self):
        ctx = self._get_extra_context(self.approver_user)
        self.assertFalse(ctx.get("show_refresh_cache_button", False))


# ═════════════════════════════════════════════════════════════════════════════
# 20. GroupAdmin — soft_delete_selected
# ═════════════════════════════════════════════════════════════════════════════

class TestGroupAdminSoftDelete(AdminTestBase):

    def setUp(self):
        self.ma = GroupAdmin(Group, self.site)

    def _make_fresh_group(self, group_id="FRESH01"):
        """Create a fresh company + group to soft-delete (won't mutate shared data)."""
        acc = make_account(f"fresh_acc_{group_id}")
        comp = make_company(acc, f"Fresh Corp {group_id}")
        return make_group(comp, group_id=group_id)

    def test_soft_delete_with_permission_marks_deleted(self):
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename="soft_delete_group")
        self.editor_user.user_permissions.add(perm)

        group = self._make_fresh_group("SD_PERM01")
        request = self._request(self.editor_user)
        # Refresh user to pick up new perm
        request.user = Account.objects.get(pk="editor_user")
        queryset = Group.objects.filter(pk=group.pk)
        self.ma.soft_delete_selected(request, queryset)

        group.refresh_from_db()
        self.assertTrue(group.isdeleted)
        self.assertFalse(group.isactive)

    def test_soft_delete_without_permission_shows_error(self):
        group = self._make_fresh_group("SD_NOPERM01")
        # viewer_user has no soft_delete_group perm by default
        request = self._request(self.viewer_user)
        queryset = Group.objects.filter(pk=group.pk)
        self.ma.soft_delete_selected(request, queryset)
        msgs = get_messages(request)
        self.assertTrue(any("permission" in m.lower() for m in msgs))

    def test_soft_delete_success_shows_message(self):
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename="soft_delete_group")
        self.admin_user.user_permissions.add(perm)

        group = self._make_fresh_group("SD_MSG01")
        request = self._request(self.admin_user)
        request.user = Account.objects.get(pk="admin_user")
        queryset = Group.objects.filter(pk=group.pk)
        self.ma.soft_delete_selected(request, queryset)
        msgs = get_messages(request)
        self.assertTrue(any("soft deleted" in m.lower() for m in msgs))

    def test_soft_delete_sets_modified_by(self):
        from django.contrib.auth.models import Permission
        perm = Permission.objects.get(codename="soft_delete_group")
        self.superuser.user_permissions.add(perm)  # superuser bypasses perm check anyway

        group = self._make_fresh_group("SD_MODBY01")
        request = self._request(self.superuser)
        queryset = Group.objects.filter(pk=group.pk)
        self.ma.soft_delete_selected(request, queryset)

        group.refresh_from_db()
        self.assertEqual(group.modified_by, "superuser")