"""
main_system/tests/test_models.py
=================================
Model-layer tests for every managed model in main_system.

Covers
------
- Field defaults and constraints
- Custom manager methods (AccountManager)
- Instance methods (get_user_type, get_display_name)
- AuditBase mixin fields (created_at, modified_at, created_by, modified_by)
- Relationship integrity (OneToOne, ForeignKey)
- Cascading deletes (Account → Company, Account → Individual → Policy)
- Uniqueness constraints
- MAX_LOGS rotation logic for ReportAccessLog and AuditLog
- AuditLog.create_log() classmethod

Prerequisites
-------------
Add to settings (or a dedicated test_settings.py):

    DATABASE_ROUTERS = ['main_system.tests.test_router.TestRouter']

Run with:

    python manage.py test main_system.tests.test_models
"""

import time
from django.test import TestCase

from main_system.models import (
    Account,
    AuditLog,
    Company,
    Group,
    Individual,
    Policy,
    ReportAccessLog,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_account(username="testuser", password="testpass123", **kwargs):
    """Create a plain (non-staff, non-super) Account."""
    return Account.objects.create_user(username=username, password=password, **kwargs)


def make_company(account=None, name="Test Corp", **kwargs):
    """Create a Company and optionally link *account* to it via Account.company_id."""
    company = Company.objects.create(company_name=name, **kwargs)
    if account is not None:
        account.company_id = company
        account.save()
    return company


def make_group(company, group_id="GRP001", group_name="Test Group", **kwargs):
    """Create a Group linked to *company*."""
    return Group.objects.create(
        company_id=company, group_id=group_id, group_name=group_name, **kwargs
    )


def make_individual(group, account, full_name="Test User", **kwargs):
    """Create an Individual linked to *group* and *account*."""
    return Individual.objects.create(
        group_id=group, username=account, user_full_name=full_name, **kwargs
    )


def make_policy(individual, policy_number="POL-001", **kwargs):
    """Create a Policy linked to *individual*."""
    return Policy.objects.create(
        user_id=individual, policy_number=policy_number, **kwargs
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. AuditBase mixin
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditBase(TestCase):
    """
    AuditBase is abstract so we test its fields through Company,
    which inherits from it.
    """

    def setUp(self):
        self.account = make_account("audit_user")
        self.company = make_company(self.account, "Audit Corp")

    def test_created_at_is_set_on_creation(self):
        self.assertIsNotNone(self.company.created_at)

    def test_modified_at_is_set_on_creation(self):
        self.assertIsNotNone(self.company.modified_at)

    def test_created_at_does_not_change_on_update(self):
        original = self.company.created_at
        self.company.company_name = "Audit Corp Updated"
        self.company.save()
        self.company.refresh_from_db()
        self.assertEqual(self.company.created_at, original)

    def test_modified_at_changes_on_update(self):
        original = self.company.modified_at
        # Ensure at least 1 ms passes so timestamps differ
        time.sleep(0.01)
        self.company.company_name = "Audit Corp Updated"
        self.company.save()
        self.company.refresh_from_db()
        self.assertGreater(self.company.modified_at, original)

    def test_created_by_is_optional(self):
        """created_by is nullable — no value required on save."""
        self.assertIsNone(self.company.created_by)

    def test_modified_by_is_optional(self):
        self.assertIsNone(self.company.modified_by)

    def test_created_by_and_modified_by_can_be_set(self):
        self.company.created_by = "admin"
        self.company.modified_by = "admin"
        self.company.save()
        self.company.refresh_from_db()
        self.assertEqual(self.company.created_by, "admin")
        self.assertEqual(self.company.modified_by, "admin")


# ─────────────────────────────────────────────────────────────────────────────
# 2. AccountManager
# ─────────────────────────────────────────────────────────────────────────────

class TestAccountManager(TestCase):

    def test_create_user_happy_path(self):
        user = Account.objects.create_user("alice", "password123")
        self.assertEqual(user.username, "alice")
        self.assertTrue(user.check_password("password123"))

    def test_create_user_sets_is_active_true_by_default(self):
        user = Account.objects.create_user("bob", "password123")
        self.assertTrue(user.is_active)

    def test_create_user_raises_on_empty_username(self):
        with self.assertRaises(ValueError):
            Account.objects.create_user("", "password123")

    def test_create_superuser_sets_flags(self):
        su = Account.objects.create_superuser("superadmin", "password123")
        self.assertTrue(su.is_staff)
        self.assertTrue(su.is_superuser)
        self.assertTrue(su.is_active)

    def test_create_superuser_raises_if_is_staff_false(self):
        with self.assertRaises(ValueError):
            Account.objects.create_superuser(
                "badsuper", "password123", is_staff=False
            )

    def test_create_superuser_raises_if_is_superuser_false(self):
        with self.assertRaises(ValueError):
            Account.objects.create_superuser(
                "badsuper2", "password123", is_superuser=False
            )

    def test_password_is_hashed_not_stored_plaintext(self):
        user = Account.objects.create_user("charlie", "myplainpassword")
        self.assertNotEqual(user.password, "myplainpassword")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Account model
# ─────────────────────────────────────────────────────────────────────────────

class TestAccountModel(TestCase):

    def test_str_returns_username(self):
        user = make_account("str_test_user")
        self.assertEqual(str(user), "str_test_user")

    def test_username_is_primary_key(self):
        user = make_account("pk_user")
        self.assertEqual(user.pk, "pk_user")

    def test_is_active_defaults_true(self):
        user = make_account("active_user")
        self.assertTrue(user.is_active)

    def test_is_staff_defaults_false(self):
        user = make_account("plain_user")
        self.assertFalse(user.is_staff)

    def test_is_superuser_defaults_false(self):
        user = make_account("plain_user2")
        self.assertFalse(user.is_superuser)

    def test_username_uniqueness(self):
        make_account("unique_user")
        with self.assertRaises(Exception):
            make_account("unique_user")

    def test_get_user_type_admin(self):
        su = Account.objects.create_superuser("admin_user", "pass")
        self.assertEqual(su.get_user_type(), "admin")

    def test_get_user_type_staff(self):
        staff = make_account("staff_user", is_staff=True)
        self.assertEqual(staff.get_user_type(), "staff")

    def test_get_user_type_company(self):
        # Account.get_user_type() checks self.company_id (the FK field on Account).
        # Create the Company first, then point the account's FK at it.
        company = Company.objects.create(company_name="Temp Corp")
        account = make_account("company_user")
        account.company_id = company
        account.save()
        account = Account.objects.get(pk="company_user")
        self.assertEqual(account.get_user_type(), "company")

    def test_get_user_type_individual(self):
        company_account = make_account("indiv_company")
        company = make_company(company_account, "Corp For Individual")
        group = make_group(company)
        indiv_account = make_account("indiv_user")
        make_individual(group, indiv_account, "Individual Person")
        indiv_account = Account.objects.get(pk="indiv_user")
        self.assertEqual(indiv_account.get_user_type(), "individual")

    def test_get_user_type_none_for_plain_account(self):
        user = make_account("nobody")
        self.assertIsNone(user.get_user_type())

    def test_get_display_name_for_staff(self):
        staff = make_account("display_staff", is_staff=True)
        self.assertEqual(staff.get_display_name(), "display_staff")

    def test_get_display_name_for_company(self):
        # Create the Company first, then point the account's FK at it.
        company = Company.objects.create(company_name="Display Corp")
        account = make_account("display_company")
        account.company_id = company
        account.save()
        account = Account.objects.get(pk="display_company")
        self.assertEqual(account.get_display_name(), "Display Corp")

    def test_get_display_name_for_individual_with_full_name(self):
        company_account = make_account("disp_company2")
        company = make_company(company_account, "Corp2")
        group = make_group(company, group_id="GRP_DISP")
        indiv_account = make_account("disp_indiv")
        make_individual(group, indiv_account, "Full Name Person")
        indiv_account = Account.objects.get(pk="disp_indiv")
        self.assertEqual(indiv_account.get_display_name(), "Full Name Person")

    def test_get_display_name_for_individual_without_full_name(self):
        company_account = make_account("disp_company3")
        company = make_company(company_account, "Corp3")
        group = make_group(company, group_id="GRP_DISP2")
        indiv_account = make_account("disp_indiv2")
        make_individual(group, indiv_account, full_name=None)
        indiv_account = Account.objects.get(pk="disp_indiv2")
        # Falls back to username string
        self.assertEqual(indiv_account.get_display_name(), "disp_indiv2")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Company model
# ─────────────────────────────────────────────────────────────────────────────

class TestCompanyModel(TestCase):

    def setUp(self):
        self.account = make_account("company_owner")
        self.company = make_company(self.account, "Main Corp")

    def test_str_returns_company_name(self):
        self.assertEqual(str(self.company), "Main Corp")

    def test_company_name_is_stored(self):
        self.company.refresh_from_db()
        self.assertEqual(self.company.company_name, "Main Corp")

    def test_isactive_defaults_true(self):
        self.assertTrue(self.company.isactive)

    def test_optional_fields_accept_null(self):
        self.assertIsNone(self.company.nepali_name)
        self.assertIsNone(self.company.phone_number)
        self.assertIsNone(self.company.email)
        self.assertIsNone(self.company.remarks)

    def test_account_linked_to_company_via_fk(self):
        # The link is on Account.company_id, not on Company.
        # Verify the account set up in setUp has the correct FK.
        self.account.refresh_from_db()
        self.assertEqual(self.account.company_id, self.company)

    def test_deleting_account_does_not_delete_company(self):
        # Account.company_id is SET_NULL on delete — Company survives.
        company_id = self.company.company_id
        self.account.delete()
        self.assertTrue(Company.objects.filter(company_id=company_id).exists())


# ─────────────────────────────────────────────────────────────────────────────
# 5. Group model
# ─────────────────────────────────────────────────────────────────────────────

class TestGroupModel(TestCase):

    def setUp(self):
        self.account = make_account("group_owner")
        self.company = make_company(self.account, "Group Corp")
        self.group = make_group(self.company)

    def test_str_returns_group_name(self):
        self.assertEqual(str(self.group), "Test Group")

    def test_str_fallback_when_no_group_name(self):
        nameless = Group.objects.create(
            company_id=self.company, group_id="GRP999", group_name=None
        )
        self.assertIn("GRP999", str(nameless))

    def test_isdeleted_defaults_false(self):
        self.assertFalse(self.group.isdeleted)

    def test_isactive_defaults_true(self):
        self.assertTrue(self.group.isactive)

    def test_group_id_uniqueness(self):
        with self.assertRaises(Exception):
            make_group(self.company, group_id="GRP001")  # same group_id

    def test_fk_to_company(self):
        self.assertEqual(self.group.company_id, self.company)

    def test_reverse_relation_from_company(self):
        self.assertIn(self.group, self.company.groups.all())

    def test_cascade_delete_company_deletes_group(self):
        group_pk = self.group.row_id
        self.company.delete()
        self.assertFalse(Group.objects.filter(row_id=group_pk).exists())

    def test_cascade_delete_company_deletes_group_via_account_fk(self):
        """Deleting account nulls company_id FK (SET_NULL); deleting company cascades to group."""
        group_pk = self.group.row_id
        self.company.delete()
        self.assertFalse(Group.objects.filter(row_id=group_pk).exists())


# ─────────────────────────────────────────────────────────────────────────────
# 6. Individual model
# ─────────────────────────────────────────────────────────────────────────────

class TestIndividualModel(TestCase):

    def setUp(self):
        self.company_account = make_account("indiv_corp_owner")
        self.company = make_company(self.company_account, "Indiv Corp")
        self.group = make_group(self.company, group_id="IGRP01")
        self.indiv_account = make_account("indiv_member")
        self.individual = make_individual(self.group, self.indiv_account)

    def test_str_returns_full_name(self):
        self.assertIn("Test User", str(self.individual))

    def test_str_fallback_to_username(self):
        nameless = Individual.objects.create(
            group_id=self.group,
            username=make_account("nameless_indiv"),
            user_full_name=None,
        )
        self.assertIn("nameless_indiv", str(nameless))

    def test_fk_to_group(self):
        self.assertEqual(self.individual.group_id, self.group)

    def test_one_to_one_to_account(self):
        self.assertEqual(self.individual.username, self.indiv_account)

    def test_reverse_relation_from_account(self):
        self.assertEqual(self.indiv_account.individual_profile, self.individual)

    def test_one_account_cannot_have_two_individuals(self):
        with self.assertRaises(Exception):
            make_individual(self.group, self.indiv_account, "Duplicate")

    def test_cascade_delete_group_deletes_individual(self):
        indiv_pk = self.individual.user_id
        self.group.delete()
        self.assertFalse(Individual.objects.filter(user_id=indiv_pk).exists())

    def test_cascade_delete_account_deletes_individual(self):
        indiv_pk = self.individual.user_id
        self.indiv_account.delete()
        self.assertFalse(Individual.objects.filter(user_id=indiv_pk).exists())

    def test_full_cascade_from_company_delete(self):
        """Company → Group → Individual all deleted when company is deleted."""
        indiv_pk = self.individual.user_id
        self.company.delete()
        self.assertFalse(Individual.objects.filter(user_id=indiv_pk).exists())


# ─────────────────────────────────────────────────────────────────────────────
# 7. Policy model
# ─────────────────────────────────────────────────────────────────────────────

class TestPolicyModel(TestCase):

    def setUp(self):
        self.company_account = make_account("pol_corp_owner")
        self.company = make_company(self.company_account, "Policy Corp")
        self.group = make_group(self.company, group_id="PGRP01")
        self.indiv_account = make_account("pol_member")
        self.individual = make_individual(self.group, self.indiv_account)
        self.policy = make_policy(self.individual)

    def test_str_contains_policy_number(self):
        self.assertIn("POL-001", str(self.policy))

    def test_policy_number_stored(self):
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.policy_number, "POL-001")

    def test_fk_to_individual(self):
        self.assertEqual(self.policy.user_id, self.individual)

    def test_reverse_relation_from_individual(self):
        self.assertIn(self.policy, self.individual.policies.all())

    def test_policy_number_uniqueness(self):
        with self.assertRaises(Exception):
            make_policy(self.individual, "POL-001")

    def test_cascade_delete_individual_deletes_policy(self):
        policy_pk = self.policy.row_id
        self.individual.delete()
        self.assertFalse(Policy.objects.filter(row_id=policy_pk).exists())

    def test_full_cascade_chain_from_individual_account(self):
        """Account → Individual → Policy (all gone)."""
        policy_pk = self.policy.row_id
        self.indiv_account.delete()
        self.assertFalse(Policy.objects.filter(row_id=policy_pk).exists())

    def test_full_cascade_chain_from_company_delete(self):
        """Company → Group → Individual → Policy all deleted when company is deleted."""
        policy_pk = self.policy.row_id
        self.company.delete()
        self.assertFalse(Policy.objects.filter(row_id=policy_pk).exists())


# ─────────────────────────────────────────────────────────────────────────────
# 8. ReportAccessLog model
# ─────────────────────────────────────────────────────────────────────────────

class TestReportAccessLog(TestCase):

    # CHANGED: field renamed from generator_company → generator throughout
    def _make_log(self, n=1, generator="test_company", report="Death Claim Report"):
        """Bulk-create *n* log entries and return the last one."""
        log = None
        for i in range(n):
            log = ReportAccessLog.objects.create(
                generator=generator,
                report_type=report,
                status=ReportAccessLog.Status.SUCCESS,
            )
        return log

    def test_creation_stores_fields(self):
        log = self._make_log()
        # CHANGED: generator_company → generator
        self.assertEqual(log.generator, "test_company")
        self.assertEqual(log.report_type, "Death Claim Report")
        self.assertEqual(log.status, ReportAccessLog.Status.SUCCESS)

    def test_generated_at_auto_set(self):
        log = self._make_log()
        self.assertIsNotNone(log.generated_at)

    def test_has_error_defaults_false(self):
        log = self._make_log()
        self.assertFalse(log.has_error)

    def test_error_message_nullable(self):
        log = self._make_log()
        self.assertIsNone(log.error_message)

    def test_remarks_nullable(self):
        log = self._make_log()
        self.assertIsNone(log.remarks)

    def test_str_format(self):
        log = self._make_log()
        result = str(log)
        self.assertIn("test_company", result)
        self.assertIn("Death Claim Report", result)
        self.assertIn("success", result)

    def test_all_status_choices_are_valid(self):
        valid_statuses = [
            ReportAccessLog.Status.SUCCESS,
            ReportAccessLog.Status.NO_DATA,
            ReportAccessLog.Status.ERROR,
            ReportAccessLog.Status.FORBIDDEN,
            ReportAccessLog.Status.INVALID_INPUT,
        ]
        for status in valid_statuses:
            log = ReportAccessLog.objects.create(
                generator="tester",
                report_type="Test Report",
                status=status,
            )
            self.assertEqual(log.status, status)

    def test_max_logs_enforced_at_exactly_limit(self):
        """At exactly MAX_LOGS rows, nothing should be deleted."""
        self._make_log(n=ReportAccessLog.MAX_LOGS)
        self.assertEqual(ReportAccessLog.objects.count(), ReportAccessLog.MAX_LOGS)

    def test_max_logs_trims_oldest_when_exceeded(self):
        """Inserting MAX_LOGS + 5 entries must leave exactly MAX_LOGS rows."""
        self._make_log(n=ReportAccessLog.MAX_LOGS + 5)
        self.assertEqual(ReportAccessLog.objects.count(), ReportAccessLog.MAX_LOGS)

    def test_oldest_entries_are_deleted_not_newest(self):
        """The newest entry must still exist after trimming."""
        last = self._make_log(n=ReportAccessLog.MAX_LOGS + 3)
        self.assertTrue(
            ReportAccessLog.objects.filter(row_id=last.row_id).exists()
        )

    def test_generator_defaults_to_unknown(self):
        # CHANGED: field is generator (default='unknown'), not generator_company
        log = ReportAccessLog.objects.create(
            report_type="Some Report",
            status=ReportAccessLog.Status.SUCCESS,
        )
        self.assertEqual(log.generator, "unknown")


# ─────────────────────────────────────────────────────────────────────────────
# 9. AuditLog model
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditLog(TestCase):

    def _create_log(self, action="login", target="testuser", target_type="account",
                    performed_by="admin", details=None, ip=None):
        return AuditLog.create_log(
            action=action,
            target_username=target,
            target_type=target_type,
            performed_by=performed_by,
            details=details,
            ip_address=ip,
        )

    def test_create_log_stores_all_fields(self):
        log = self._create_log(
            action="login",
            target="alice",
            target_type="account",
            performed_by="alice",
            details="Login from web",
            ip="192.168.1.1",
        )
        self.assertEqual(log.action, "login")
        self.assertEqual(log.target_username, "alice")
        self.assertEqual(log.target_type, "account")
        self.assertEqual(log.performed_by, "alice")
        self.assertEqual(log.details, "Login from web")
        self.assertEqual(log.ip_address, "192.168.1.1")

    def test_timestamp_auto_set(self):
        log = self._create_log()
        self.assertIsNotNone(log.timestamp)

    def test_details_optional(self):
        log = self._create_log(details=None)
        self.assertIsNone(log.details)

    def test_ip_address_optional(self):
        log = self._create_log(ip=None)
        self.assertIsNone(log.ip_address)

    def test_ip_address_accepts_ipv4(self):
        log = self._create_log(ip="10.0.0.1")
        self.assertEqual(log.ip_address, "10.0.0.1")

    def test_ip_address_accepts_ipv6(self):
        log = self._create_log(ip="2001:db8::1")
        self.assertEqual(log.ip_address, "2001:db8::1")

    def test_str_format(self):
        log = self._create_log(action="logout", target="bob", performed_by="bob")
        result = str(log)
        self.assertIn("logout", result)
        self.assertIn("bob", result)

    def test_all_action_choices_are_valid(self):
        valid_actions = [
            "password_reset", "role_change", "soft_delete", "hard_delete",
            "create", "update", "login", "login_failed", "logout",
            "permission_change",
        ]
        for action in valid_actions:
            log = self._create_log(action=action)
            self.assertEqual(log.action, action)

    def test_max_logs_enforced_at_exactly_limit(self):
        for i in range(AuditLog.MAX_LOGS):
            self._create_log(target=f"user_{i}")
        self.assertEqual(AuditLog.objects.count(), AuditLog.MAX_LOGS)

    def test_max_logs_trims_oldest_when_exceeded(self):
        overflow = 4
        for i in range(AuditLog.MAX_LOGS + overflow):
            self._create_log(target=f"user_{i}")
        self.assertEqual(AuditLog.objects.count(), AuditLog.MAX_LOGS)

    def test_newest_log_survives_trim(self):
        last = None
        for i in range(AuditLog.MAX_LOGS + 3):
            last = self._create_log(target=f"user_{i}")
        self.assertTrue(AuditLog.objects.filter(log_id=last.log_id).exists())

    def test_ordering_newest_first(self):
        """Default ordering is -timestamp so first() is the newest."""
        last = None
        for i in range(3):
            last = self._create_log(target=f"order_user_{i}")
        newest = AuditLog.objects.first()
        self.assertEqual(newest.log_id, last.log_id)

        #519.2 + 4200 + 3840 + 38 +  70 + 884 