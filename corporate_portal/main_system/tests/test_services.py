"""
main_system/tests/test_services.py
====================================
Test suite for main_system/services.py

Covers:
  - PermissionMixin.check_permission
  - CompanyService  : create, update, soft_delete, hard_delete, approve,
                      validate_group_availability
  - AccountService  : can_modify_account, reset_password
  - IndividualService: create, update, soft_delete, hard_delete, approve
  - AuditLog rotation (MAX_LOGS=20) triggered through service calls

Run with:
    python manage.py test main_system.tests.test_services
        --settings=corporate_portal.test_settings
"""

from unittest.mock import patch, MagicMock

from django.contrib.auth.models import Group as DjangoGroup
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from main_system.models import Account, AuditLog, Company, Group, Individual
from main_system.services import (
    AccountService,
    CompanyService,
    IndividualService,
    PermissionMixin,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_account(username, password="pass1234", is_staff=False, is_superuser=False):
    """Create and return a bare Account (no company/individual profile)."""
    return Account.objects.create_user(
        username=username,
        password=password,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


def make_company(username_str, company_name="Test Corp", isactive=True):
    """
    Create Account + Company and return the Company instance.
    """
    account = make_account(username_str)
    return Company.objects.create(
        username=account,
        company_name=company_name,
        isactive=isactive,
    )


def make_group(company, group_id, group_name="Test Group", isdeleted=False, isactive=True):
    """Create and return a Group belonging to *company*."""
    return Group.objects.create(
        company_id=company,
        group_id=group_id,
        group_name=group_name,
        isdeleted=isdeleted,
        isactive=isactive,
    )


def make_individual(group, username_str, full_name="Test User"):
    """Create Account + Individual and return the Individual instance."""
    account = make_account(username_str)
    return Individual.objects.create(
        username=account,
        group_id=group,
        user_full_name=full_name,
    )


def superuser(username="su"):
    """Return a superuser Account (bypasses all permission checks)."""
    return make_account(username, is_superuser=True)


def staff_user_with_perm(username, perm_codename):
    """
    Return a staff Account that has *perm_codename* via has_perm.
    We patch has_perm at the call site, so this just needs to be
    a valid authenticated user — permissions are mocked per-test.
    """
    return make_account(username, is_staff=True)


# ─────────────────────────────────────────────────────────────────────────────
# PermissionMixin
# ─────────────────────────────────────────────────────────────────────────────

class PermissionMixinTests(TestCase):

    def test_superuser_always_passes(self):
        """Superuser bypasses has_perm entirely."""
        su = superuser("su_perm")
        # No mock needed — is_superuser short-circuits
        result = PermissionMixin.check_permission(su, "main_system.add_company")
        self.assertTrue(result)

    def test_none_user_raises_permission_denied(self):
        with self.assertRaises(PermissionDenied):
            PermissionMixin.check_permission(None, "main_system.add_company")

    def test_none_user_returns_false_when_raise_false(self):
        result = PermissionMixin.check_permission(
            None, "main_system.add_company", raise_exception=False
        )
        self.assertFalse(result)

    def test_user_without_perm_raises(self):
        user = make_account("noperm_user")
        with patch.object(user, "has_perm", return_value=False):
            with self.assertRaises(PermissionDenied):
                PermissionMixin.check_permission(user, "main_system.add_company")

    def test_user_without_perm_returns_false_when_raise_false(self):
        user = make_account("noperm_user2")
        with patch.object(user, "has_perm", return_value=False):
            result = PermissionMixin.check_permission(
                user, "main_system.add_company", raise_exception=False
            )
        self.assertFalse(result)

    def test_user_with_perm_returns_true(self):
        user = make_account("hasperm_user")
        with patch.object(user, "has_perm", return_value=True):
            result = PermissionMixin.check_permission(user, "main_system.add_company")
        self.assertTrue(result)


# ─────────────────────────────────────────────────────────────────────────────
# CompanyService.validate_group_availability
# ─────────────────────────────────────────────────────────────────────────────

class ValidateGroupAvailabilityTests(TestCase):

    def setUp(self):
        self.company_a = make_company("company_a_user", "Company A")
        self.company_b = make_company("company_b_user", "Company B")
        self.group = make_group(self.company_a, "G001", "Group One")

    def test_no_group_ids_returns_none(self):
        result = CompanyService.validate_group_availability([])
        self.assertIsNone(result)

    def test_unassigned_group_ids_return_none(self):
        result = CompanyService.validate_group_availability(["G999"])
        self.assertIsNone(result)

    def test_conflict_detected_for_assigned_group(self):
        conflicts = CompanyService.validate_group_availability(["G001"])
        self.assertIsNotNone(conflicts)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["group_id"], "G001")
        self.assertEqual(conflicts[0]["company_name"], "Company A")

    def test_exclude_own_company_removes_conflict(self):
        # Editing company_a itself — G001 should not conflict
        result = CompanyService.validate_group_availability(
            ["G001"], exclude_company_id=self.company_a.company_id
        )
        self.assertIsNone(result)

    def test_deleted_group_not_treated_as_conflict(self):
        make_group(self.company_b, "G002", "Group Two", isdeleted=True)
        result = CompanyService.validate_group_availability(["G002"])
        self.assertIsNone(result)

    def test_multiple_conflicts_all_reported(self):
        make_group(self.company_b, "G003", "Group Three")
        conflicts = CompanyService.validate_group_availability(["G001", "G003"])
        conflict_ids = {c["group_id"] for c in conflicts}
        self.assertIn("G001", conflict_ids)
        self.assertIn("G003", conflict_ids)


# ─────────────────────────────────────────────────────────────────────────────
# CompanyService.create_company
# ─────────────────────────────────────────────────────────────────────────────

class CreateCompanyServiceTests(TestCase):

    def setUp(self):
        self.actor = superuser("create_actor")
        self.company_data = {"company_name": "New Corp", "isactive": True}
        self.groups_lookup = {"G010": "Group Ten", "G011": "Group Eleven"}

    def test_creates_account_and_company(self):
        company = CompanyService.create_company(
            username="newcorp_user",
            password="secure123",
            company_data=self.company_data.copy(),
            group_ids=["G010"],
            groups_lookup=self.groups_lookup,
            user=self.actor,
        )
        self.assertIsInstance(company, Company)
        self.assertTrue(Account.objects.filter(username="newcorp_user").exists())

    def test_creates_groups(self):
        CompanyService.create_company(
            username="newcorp_grp",
            password="secure123",
            company_data={"company_name": "Grp Corp", "isactive": True},
            group_ids=["G010", "G011"],
            groups_lookup=self.groups_lookup,
            user=self.actor,
        )
        company = Company.objects.get(company_name="Grp Corp")
        self.assertEqual(Group.objects.filter(company_id=company).count(), 2)

    def test_audit_fields_set_on_account_and_company(self):
        company = CompanyService.create_company(
            username="audit_user",
            password="pass",
            company_data={"company_name": "Audit Corp", "isactive": True},
            group_ids=[],
            groups_lookup={},
            user=self.actor,
        )
        self.assertEqual(company.created_by, self.actor.username)
        account = Account.objects.get(username="audit_user")
        self.assertEqual(account.created_by, self.actor.username)

    def test_audit_log_created_on_success(self):
        CompanyService.create_company(
            username="log_corp_user",
            password="pass",
            company_data={"company_name": "Log Corp", "isactive": True},
            group_ids=["G010"],
            groups_lookup=self.groups_lookup,
            user=self.actor,
        )
        log = AuditLog.objects.filter(
            action="create", target_username="log_corp_user"
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.performed_by, self.actor.username)

    def test_missing_username_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            CompanyService.create_company(
                username="",
                password="pass",
                company_data={"company_name": "X"},
                group_ids=[],
                groups_lookup={},
                user=self.actor,
            )

    def test_missing_password_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            CompanyService.create_company(
                username="no_pass_user",
                password="",
                company_data={"company_name": "X"},
                group_ids=[],
                groups_lookup={},
                user=self.actor,
            )

    def test_group_conflict_raises_validation_error_and_rolls_back(self):
        # G010 already assigned to existing company
        existing = make_company("existing_owner", "Existing Corp")
        make_group(existing, "G010", "Group Ten")

        with self.assertRaises(ValidationError):
            CompanyService.create_company(
                username="conflict_user",
                password="pass",
                company_data={"company_name": "Conflict Corp"},
                group_ids=["G010"],
                groups_lookup=self.groups_lookup,
                user=self.actor,
            )
        # Transaction rolled back — no partial account created
        self.assertFalse(Account.objects.filter(username="conflict_user").exists())

    def test_no_permission_raises_permission_denied(self):
        unprivileged = make_account("unpriv_create")
        with patch.object(unprivileged, "has_perm", return_value=False):
            with self.assertRaises(PermissionDenied):
                CompanyService.create_company(
                    username="blocked_user",
                    password="pass",
                    company_data={"company_name": "Blocked"},
                    group_ids=[],
                    groups_lookup={},
                    user=unprivileged,
                )

    def test_no_user_raises_permission_denied(self):
        """
        user=None fails immediately at check_permission — PermissionDenied is
        raised before any DB write, so no company or audit log is created.
        """
        before_companies = Company.objects.count()
        before_logs = AuditLog.objects.count()
        with self.assertRaises(PermissionDenied):
            CompanyService.create_company(
                username="anon_corp",
                password="pass",
                company_data={"company_name": "Anon Corp", "isactive": True},
                group_ids=[],
                groups_lookup={},
                user=None,
            )
        self.assertEqual(Company.objects.count(), before_companies)
        self.assertEqual(AuditLog.objects.count(), before_logs)


# ─────────────────────────────────────────────────────────────────────────────
# CompanyService.update_company
# ─────────────────────────────────────────────────────────────────────────────

class UpdateCompanyServiceTests(TestCase):

    def setUp(self):
        self.actor = superuser("update_actor")
        self.company = make_company("upd_corp_user", "Update Corp", isactive=True)
        make_group(self.company, "G020", "Group Twenty")

    def test_updates_company_name(self):
        CompanyService.update_company(
            company=self.company,
            company_data={"company_name": "Renamed Corp"},
            user=self.actor,
        )
        self.company.refresh_from_db()
        self.assertEqual(self.company.company_name, "Renamed Corp")

    def test_audit_log_created_when_name_changes(self):
        CompanyService.update_company(
            company=self.company,
            company_data={"company_name": "Logged Corp"},
            user=self.actor,
        )
        log = AuditLog.objects.filter(
            action="update", target_username=self.company.username.username
        ).first()
        self.assertIsNotNone(log)

    def test_no_audit_log_when_nothing_changes(self):
        before = AuditLog.objects.count()
        CompanyService.update_company(
            company=self.company,
            company_data={"company_name": "Update Corp"},  # same name
            user=self.actor,
        )
        self.assertEqual(AuditLog.objects.count(), before)

    def test_password_update(self):
        CompanyService.update_company(
            company=self.company,
            password="new_secret_pass",
            user=self.actor,
        )
        account = Account.objects.get(username=self.company.username.username)
        self.assertTrue(account.check_password("new_secret_pass"))

    def test_username_change_creates_new_account_and_deletes_old(self):
        old_username = self.company.username.username
        CompanyService.update_company(
            company=self.company,
            username="brand_new_user",
            user=self.actor,
        )
        self.assertFalse(Account.objects.filter(username=old_username).exists())
        self.assertTrue(Account.objects.filter(username="brand_new_user").exists())

    def test_group_replacement(self):
        make_group(self.company, "G021", "Group TwentyOne")
        CompanyService.update_company(
            company=self.company,
            group_ids=["G022"],
            groups_lookup={"G022": "Group TwentyTwo"},
            user=self.actor,
        )
        active_groups = Group.objects.filter(company_id=self.company, isdeleted=False)
        self.assertEqual(active_groups.count(), 1)
        self.assertEqual(active_groups.first().group_id, "G022")

    def test_inactive_company_cascades_to_groups(self):
        CompanyService.update_company(
            company=self.company,
            company_data={"isactive": False},
            user=self.actor,
        )
        inactive_groups = Group.objects.filter(
            company_id=self.company, isactive=False
        )
        self.assertTrue(inactive_groups.exists())

    def test_group_conflict_rolls_back(self):
        other_company = make_company("other_owner", "Other Corp")
        make_group(other_company, "G099", "Taken Group")

        with self.assertRaises(ValidationError):
            CompanyService.update_company(
                company=self.company,
                group_ids=["G099"],
                groups_lookup={"G099": "Taken Group"},
                user=self.actor,
            )
        # Original group should still be present
        self.assertTrue(
            Group.objects.filter(company_id=self.company, group_id="G020").exists()
        )

    def test_no_permission_raises_permission_denied(self):
        unprivileged = make_account("unpriv_update")
        with patch.object(unprivileged, "has_perm", return_value=False):
            with self.assertRaises(PermissionDenied):
                CompanyService.update_company(
                    company=self.company,
                    company_data={"company_name": "Hacked"},
                    user=unprivileged,
                )

    def test_reactivating_existing_group_on_update(self):
        """A group previously soft-deleted on the company is restored when re-added."""
        Group.objects.filter(company_id=self.company, group_id="G020").update(
            isdeleted=True, isactive=False
        )
        CompanyService.update_company(
            company=self.company,
            group_ids=["G020"],
            groups_lookup={"G020": "Group Twenty"},
            user=self.actor,
        )
        group = Group.objects.get(company_id=self.company, group_id="G020")
        self.assertFalse(group.isdeleted)


# ─────────────────────────────────────────────────────────────────────────────
# CompanyService.soft_delete_company
# ─────────────────────────────────────────────────────────────────────────────

class SoftDeleteCompanyServiceTests(TestCase):

    def setUp(self):
        self.actor = superuser("soft_del_actor")
        self.company = make_company("softdel_user", "SoftDel Corp", isactive=True)
        make_group(self.company, "GSD1", "SD Group One")
        make_group(self.company, "GSD2", "SD Group Two")

    def test_company_isactive_set_false(self):
        CompanyService.soft_delete_company(self.company, user=self.actor)
        self.company.refresh_from_db()
        self.assertFalse(self.company.isactive)

    def test_account_is_active_set_false(self):
        CompanyService.soft_delete_company(self.company, user=self.actor)
        account = Account.objects.get(username="softdel_user")
        self.assertFalse(account.is_active)

    def test_all_groups_soft_deleted(self):
        CompanyService.soft_delete_company(self.company, user=self.actor)
        active_groups = Group.objects.filter(
            company_id=self.company, isdeleted=False
        )
        self.assertEqual(active_groups.count(), 0)

    def test_audit_log_created(self):
        CompanyService.soft_delete_company(self.company, user=self.actor)
        log = AuditLog.objects.filter(
            action="soft_delete", target_username="softdel_user"
        ).first()
        self.assertIsNotNone(log)

    def test_no_permission_raises_permission_denied(self):
        unprivileged = make_account("unpriv_soft_del")
        with patch.object(unprivileged, "has_perm", return_value=False):
            with self.assertRaises(PermissionDenied):
                CompanyService.soft_delete_company(self.company, user=unprivileged)


# ─────────────────────────────────────────────────────────────────────────────
# CompanyService.hard_delete_company
# ─────────────────────────────────────────────────────────────────────────────

class HardDeleteCompanyServiceTests(TestCase):

    def setUp(self):
        self.actor = superuser("hard_del_actor")
        self.company = make_company("harddel_user", "HardDel Corp")

    def test_company_and_account_deleted(self):
        CompanyService.hard_delete_company(self.company, user=self.actor)
        self.assertFalse(Company.objects.filter(company_name="HardDel Corp").exists())
        self.assertFalse(Account.objects.filter(username="harddel_user").exists())

    def test_returns_true(self):
        result = CompanyService.hard_delete_company(self.company, user=self.actor)
        self.assertTrue(result)

    def test_audit_log_created_before_delete(self):
        CompanyService.hard_delete_company(self.company, user=self.actor)
        log = AuditLog.objects.filter(
            action="hard_delete", target_username="harddel_user"
        ).first()
        self.assertIsNotNone(log)

    def test_no_permission_raises_permission_denied(self):
        unprivileged = make_account("unpriv_hard_del")
        with patch.object(unprivileged, "has_perm", return_value=False):
            with self.assertRaises(PermissionDenied):
                CompanyService.hard_delete_company(self.company, user=unprivileged)


# ─────────────────────────────────────────────────────────────────────────────
# CompanyService.approve_company
# ─────────────────────────────────────────────────────────────────────────────

class ApproveCompanyServiceTests(TestCase):

    def setUp(self):
        self.actor = superuser("approve_actor")
        self.company = make_company("approve_corp_user", "Approve Corp", isactive=False)
        make_group(self.company, "GAP1", "Approve Group", isdeleted=True, isactive=False)

    def test_company_isactive_set_true(self):
        with patch.object(self.actor, "has_perm", return_value=True):
            CompanyService.approve_company(self.company, user=self.actor)
        self.company.refresh_from_db()
        self.assertTrue(self.company.isactive)

    def test_account_is_active_set_true(self):
        with patch.object(self.actor, "has_perm", return_value=True):
            CompanyService.approve_company(self.company, user=self.actor)
        account = Account.objects.get(username="approve_corp_user")
        self.assertTrue(account.is_active)

    def test_groups_reactivated(self):
        with patch.object(self.actor, "has_perm", return_value=True):
            CompanyService.approve_company(self.company, user=self.actor)
        group = Group.objects.get(company_id=self.company, group_id="GAP1")
        self.assertTrue(group.isactive)
        self.assertFalse(group.isdeleted)

    def test_no_permission_raises_permission_denied(self):
        unprivileged = make_account("unpriv_approve")
        with patch.object(unprivileged, "has_perm", return_value=False):
            with self.assertRaises(PermissionDenied):
                CompanyService.approve_company(self.company, user=unprivileged)


# ─────────────────────────────────────────────────────────────────────────────
# AccountService.can_modify_account
# ─────────────────────────────────────────────────────────────────────────────

class CanModifyAccountTests(TestCase):

    def test_superuser_can_modify_any(self):
        su = superuser("su_modify")
        target = make_account("target_any")
        result = AccountService.can_modify_account(su, target)
        self.assertTrue(result)

    def test_unauthenticated_user_raises(self):
        """None user raises PermissionDenied."""
        target = make_account("target_unauth")
        with self.assertRaises(PermissionDenied):
            AccountService.can_modify_account(None, target)

    def test_self_modification_raises(self):
        user = make_account("self_mod_user")
        with self.assertRaises(PermissionDenied):
            AccountService.can_modify_account(user, user)

    def test_editor_cannot_modify_staff(self):
        editor = make_account("editor_user")
        staff_target = make_account("staff_target", is_staff=True)

        # Assign Django Group 'Editor' to editor
        editor_group, _ = DjangoGroup.objects.get_or_create(name="Editor")
        editor.groups.add(editor_group)

        with self.assertRaises(PermissionDenied):
            AccountService.can_modify_account(editor, staff_target)

    def test_admin_cannot_modify_superuser(self):
        admin = make_account("admin_user", is_staff=True)
        su_target = make_account("su_target", is_superuser=True)

        admin_group, _ = DjangoGroup.objects.get_or_create(name="Admin")
        admin.groups.add(admin_group)

        with self.assertRaises(PermissionDenied):
            AccountService.can_modify_account(admin, su_target)

    def test_regular_staff_can_modify_non_staff(self):
        staff = make_account("regular_staff", is_staff=True)
        target = make_account("regular_target")
        result = AccountService.can_modify_account(staff, target)
        self.assertTrue(result)


# ─────────────────────────────────────────────────────────────────────────────
# AccountService.reset_password
# ─────────────────────────────────────────────────────────────────────────────

class ResetPasswordServiceTests(TestCase):

    def setUp(self):
        self.actor = superuser("reset_actor")

    def test_password_actually_changes(self):
        target = make_account("pw_target", password="old_password")
        AccountService.reset_password(target, "new_password", user=self.actor)
        target.refresh_from_db()
        self.assertTrue(target.check_password("new_password"))

    def test_audit_log_created(self):
        target = make_account("pw_log_target")
        AccountService.reset_password(target, "new_pass_123", user=self.actor)
        log = AuditLog.objects.filter(
            action="password_reset", target_username="pw_log_target"
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.performed_by, self.actor.username)

    def test_modified_by_updated(self):
        target = make_account("pw_mod_target")
        AccountService.reset_password(target, "new_pass_456", user=self.actor)
        target.refresh_from_db()
        self.assertEqual(target.modified_by, self.actor.username)

    def test_self_reset_raises_permission_denied(self):
        """
        A non-superuser cannot reset their own password through the service.
        Note: superusers bypass the self-modification check entirely (is_superuser
        short-circuits before the username comparison), so we use a regular
        staff user here to hit the actual guard.
        """
        regular_staff = make_account("self_reset_staff", is_staff=True)
        with self.assertRaises(PermissionDenied):
            AccountService.reset_password(regular_staff, "self_pass", user=regular_staff)

    def test_no_audit_log_when_no_user(self):
        """Resetting without a user actor skips audit log."""
        # Need a separate actor to avoid the self-modification check
        target = make_account("pw_no_user_target")
        before = AuditLog.objects.count()
        # Without user we need to bypass can_modify_account which requires a user
        # We pass user=None which means can_modify_account will raise PermissionDenied.
        # This test documents that behaviour.
        with self.assertRaises(PermissionDenied):
            AccountService.reset_password(target, "pass", user=None)
        self.assertEqual(AuditLog.objects.count(), before)


# ─────────────────────────────────────────────────────────────────────────────
# IndividualService.create_individual
# ─────────────────────────────────────────────────────────────────────────────

class CreateIndividualServiceTests(TestCase):

    def setUp(self):
        self.actor = superuser("ind_create_actor")
        # Company + group needed for individual FK
        self.company = make_company("ind_owner_corp", "Owner Corp")
        self.group = make_group(self.company, "IG001", "Ind Group One")

    def _individual_data(self, full_name="John Doe"):
        return {"group_id": self.group, "user_full_name": full_name}

    def test_creates_account_and_individual(self):
        ind = IndividualService.create_individual(
            username="ind_user_1",
            password="ind_pass",
            individual_data=self._individual_data(),
            user=self.actor,
        )
        self.assertIsInstance(ind, Individual)
        self.assertTrue(Account.objects.filter(username="ind_user_1").exists())

    def test_audit_fields_set(self):
        ind = IndividualService.create_individual(
            username="ind_audit",
            password="ind_pass",
            individual_data=self._individual_data(),
            user=self.actor,
        )
        self.assertEqual(ind.created_by, self.actor.username)

    def test_audit_log_created(self):
        IndividualService.create_individual(
            username="ind_log",
            password="ind_pass",
            individual_data=self._individual_data(),
            user=self.actor,
        )
        log = AuditLog.objects.filter(
            action="create", target_username="ind_log", target_type="individual"
        ).first()
        self.assertIsNotNone(log)

    def test_missing_username_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            IndividualService.create_individual(
                username="",
                password="pass",
                individual_data=self._individual_data(),
                user=self.actor,
            )

    def test_missing_password_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            IndividualService.create_individual(
                username="ind_nopass",
                password="",
                individual_data=self._individual_data(),
                user=self.actor,
            )

    def test_no_permission_raises_permission_denied(self):
        unprivileged = make_account("unpriv_ind_create")
        with patch.object(unprivileged, "has_perm", return_value=False):
            with self.assertRaises(PermissionDenied):
                IndividualService.create_individual(
                    username="blocked_ind",
                    password="pass",
                    individual_data=self._individual_data(),
                    user=unprivileged,
                )

    def test_transaction_rollback_on_error(self):
        """If individual creation fails mid-way, account should not persist."""
        # Pass a bad group FK to trigger DB error during Individual.objects.create
        bad_data = {"group_id": None, "user_full_name": "Bad"}
        with self.assertRaises(Exception):
            IndividualService.create_individual(
                username="rollback_ind",
                password="pass",
                individual_data=bad_data,
                user=self.actor,
            )
        self.assertFalse(Account.objects.filter(username="rollback_ind").exists())


# ─────────────────────────────────────────────────────────────────────────────
# IndividualService.update_individual
# ─────────────────────────────────────────────────────────────────────────────

class UpdateIndividualServiceTests(TestCase):

    def setUp(self):
        self.actor = superuser("ind_update_actor")
        self.company = make_company("ind_upd_corp", "Upd Corp")
        self.group = make_group(self.company, "IUG01", "Ind Upd Group")
        self.individual = make_individual(self.group, "ind_upd_user", "Original Name")

    def test_updates_full_name(self):
        IndividualService.update_individual(
            individual=self.individual,
            individual_data={"user_full_name": "Updated Name"},
            user=self.actor,
        )
        self.individual.refresh_from_db()
        self.assertEqual(self.individual.user_full_name, "Updated Name")

    def test_audit_log_created_on_change(self):
        IndividualService.update_individual(
            individual=self.individual,
            individual_data={"user_full_name": "Logged Name"},
            user=self.actor,
        )
        log = AuditLog.objects.filter(
            action="update",
            target_username=self.individual.username.username,
        ).first()
        self.assertIsNotNone(log)

    def test_password_update(self):
        IndividualService.update_individual(
            individual=self.individual,
            password="new_ind_pass",
            user=self.actor,
        )
        account = Account.objects.get(username="ind_upd_user")
        self.assertTrue(account.check_password("new_ind_pass"))

    def test_username_change(self):
        IndividualService.update_individual(
            individual=self.individual,
            username="ind_new_username",
            user=self.actor,
        )
        self.assertTrue(Account.objects.filter(username="ind_new_username").exists())
        self.assertFalse(Account.objects.filter(username="ind_upd_user").exists())

    def test_no_permission_raises(self):
        unprivileged = make_account("unpriv_ind_upd")
        with patch.object(unprivileged, "has_perm", return_value=False):
            with self.assertRaises(PermissionDenied):
                IndividualService.update_individual(
                    individual=self.individual,
                    individual_data={"user_full_name": "Hacked"},
                    user=unprivileged,
                )


# ─────────────────────────────────────────────────────────────────────────────
# IndividualService.soft_delete_individual
# ─────────────────────────────────────────────────────────────────────────────

class SoftDeleteIndividualServiceTests(TestCase):

    def setUp(self):
        self.actor = superuser("ind_soft_actor")
        self.company = make_company("ind_soft_corp", "Soft Corp")
        self.group = make_group(self.company, "ISG01", "Ind Soft Group")
        self.individual = make_individual(self.group, "ind_soft_user", "Soft User")

    def test_account_deactivated(self):
        IndividualService.soft_delete_individual(self.individual, user=self.actor)
        account = Account.objects.get(username="ind_soft_user")
        self.assertFalse(account.is_active)

    def test_audit_log_created(self):
        IndividualService.soft_delete_individual(self.individual, user=self.actor)
        log = AuditLog.objects.filter(
            action="soft_delete", target_username="ind_soft_user"
        ).first()
        self.assertIsNotNone(log)

    def test_individual_record_still_exists(self):
        """Soft delete must NOT remove the Individual row."""
        IndividualService.soft_delete_individual(self.individual, user=self.actor)
        self.assertTrue(Individual.objects.filter(pk=self.individual.pk).exists())

    def test_no_permission_raises(self):
        unprivileged = make_account("unpriv_ind_soft")
        with patch.object(unprivileged, "has_perm", return_value=False):
            with self.assertRaises(PermissionDenied):
                IndividualService.soft_delete_individual(
                    self.individual, user=unprivileged
                )


# ─────────────────────────────────────────────────────────────────────────────
# IndividualService.hard_delete_individual
# ─────────────────────────────────────────────────────────────────────────────

class HardDeleteIndividualServiceTests(TestCase):

    def setUp(self):
        self.actor = superuser("ind_hard_actor")
        self.company = make_company("ind_hard_corp", "Hard Corp")
        self.group = make_group(self.company, "IHG01", "Ind Hard Group")
        self.individual = make_individual(self.group, "ind_hard_user", "Hard User")

    def test_individual_and_account_deleted(self):
        IndividualService.hard_delete_individual(self.individual, user=self.actor)
        self.assertFalse(Individual.objects.filter(user_full_name="Hard User").exists())
        self.assertFalse(Account.objects.filter(username="ind_hard_user").exists())

    def test_returns_true(self):
        result = IndividualService.hard_delete_individual(self.individual, user=self.actor)
        self.assertTrue(result)

    def test_audit_log_created_before_delete(self):
        IndividualService.hard_delete_individual(self.individual, user=self.actor)
        log = AuditLog.objects.filter(
            action="hard_delete", target_username="ind_hard_user"
        ).first()
        self.assertIsNotNone(log)

    def test_no_permission_raises(self):
        unprivileged = make_account("unpriv_ind_hard")
        with patch.object(unprivileged, "has_perm", return_value=False):
            with self.assertRaises(PermissionDenied):
                IndividualService.hard_delete_individual(
                    self.individual, user=unprivileged
                )


# ─────────────────────────────────────────────────────────────────────────────
# IndividualService.approve_individual
# ─────────────────────────────────────────────────────────────────────────────

class ApproveIndividualServiceTests(TestCase):

    def setUp(self):
        self.actor = superuser("ind_approve_actor")
        self.company = make_company("ind_app_corp", "App Corp")
        self.group = make_group(self.company, "IAG01", "Ind App Group")
        self.individual = make_individual(self.group, "ind_app_user", "App User")
        # Start deactivated
        self.individual.username.is_active = False
        self.individual.username.save()

    def test_account_activated(self):
        with patch.object(self.actor, "has_perm", return_value=True):
            IndividualService.approve_individual(self.individual, user=self.actor)
        account = Account.objects.get(username="ind_app_user")
        self.assertTrue(account.is_active)

    def test_modified_by_set(self):
        with patch.object(self.actor, "has_perm", return_value=True):
            IndividualService.approve_individual(self.individual, user=self.actor)
        self.individual.refresh_from_db()
        self.assertEqual(self.individual.modified_by, self.actor.username)

    def test_no_permission_raises(self):
        unprivileged = make_account("unpriv_ind_app")
        with patch.object(unprivileged, "has_perm", return_value=False):
            with self.assertRaises(PermissionDenied):
                IndividualService.approve_individual(
                    self.individual, user=unprivileged
                )


# ─────────────────────────────────────────────────────────────────────────────
# AuditLog rotation (MAX_LOGS = 20)
# ─────────────────────────────────────────────────────────────────────────────

class AuditLogRotationTests(TestCase):
    """
    AuditLog.create_log enforces a hard cap of MAX_LOGS=20.
    We verify this by driving log creation through the service layer,
    confirming the oldest entries are pruned automatically.
    """

    def _flood_logs(self, count, actor):
        """Create *count* audit log entries directly via create_log."""
        for i in range(count):
            AuditLog.create_log(
                action="login",
                target_username=f"flood_user_{i}",
                target_type="account",
                performed_by=actor.username,
            )

    def test_log_count_never_exceeds_max(self):
        actor = superuser("rotation_actor")
        self._flood_logs(AuditLog.MAX_LOGS + 5, actor)
        self.assertLessEqual(AuditLog.objects.count(), AuditLog.MAX_LOGS)

    def test_oldest_logs_pruned_first(self):
        actor = superuser("prune_actor")
        # Fill exactly at the limit
        self._flood_logs(AuditLog.MAX_LOGS, actor)
        # The earliest entry
        oldest = AuditLog.objects.order_by("timestamp").first()
        oldest_id = oldest.log_id

        # Push one more over the limit
        AuditLog.create_log(
            action="login",
            target_username="one_more",
            target_type="account",
            performed_by=actor.username,
        )
        # Oldest must have been removed
        self.assertFalse(AuditLog.objects.filter(log_id=oldest_id).exists())

    def test_newest_log_is_retained_after_rotation(self):
        actor = superuser("newest_actor")
        self._flood_logs(AuditLog.MAX_LOGS, actor)

        new_log = AuditLog.create_log(
            action="create",
            target_username="keep_me",
            target_type="company",
            performed_by=actor.username,
        )
        self.assertTrue(AuditLog.objects.filter(log_id=new_log.log_id).exists())

    def test_service_create_company_respects_log_cap(self):
        """End-to-end: creating many companies must not overflow the log."""
        actor = superuser("cap_actor")
        for i in range(AuditLog.MAX_LOGS + 3):
            CompanyService.create_company(
                username=f"cap_corp_{i}",
                password="pass",
                company_data={"company_name": f"Cap Corp {i}", "isactive": True},
                group_ids=[],
                groups_lookup={},
                user=actor,
            )
        self.assertLessEqual(AuditLog.objects.count(), AuditLog.MAX_LOGS)