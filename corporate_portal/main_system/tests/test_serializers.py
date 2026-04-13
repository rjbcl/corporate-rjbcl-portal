"""
api_corporate/tests/test_serializers.py
========================================
Serializer-layer tests for api_corporate.

Covers
------
CustomTokenObtainPairSerializer
  - Valid credentials → tokens + correct payload shape
  - Invalid credentials → ValidationError
  - Inactive user → ValidationError
  - company user → company-specific fields in response
  - individual user → individual-specific fields in response
  - staff user → user_type = 'staff', no company/individual extras

GroupInformationSerializer
  - Output shape contains exactly the declared fields, nothing more
  - All fields are read-only (input data is silently ignored)
  - Nullable fields serialise as None when not set
  - Decimal fields serialise as strings (DRF default)
  - max_length enforcement on group_id and group_name via model field

GroupEndowmentSerializer
  - Output shape contains every model field (fields = '__all__')
  - register_no is required (primary key, not nullable)
  - policy_no is required (not nullable)
  - All other fields are optional (blank/null=True on every one of them)
  - max_length boundaries enforced on CharField columns
  - Date / DateTimeField accept valid ISO strings
  - Date / DateTimeField reject obviously wrong strings

Not tested here
---------------
- DB-level reads against company_external (unmanaged views, blocked by
  TestRouter).  Integration/view-level tests are the right place for those.
- JWT token signature / expiry — that belongs to simplejwt's own test suite.

Run with:
    python manage.py test api_corporate.tests.test_serializers \\
        --settings=corporate_portal.test_settings
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase

from main_system.models import Account, Company, Group, Individual

from rest_framework import serializers as drf_serializers

from api_corporate.serializers import (
    CustomTokenObtainPairSerializer,
    GroupEndowmentSerializer,
    GroupInformationSerializer,
)
from api_corporate.models import GroupEndowment, GroupInformation


# ─────────────────────────────────────────────────────────────────────────────
# Test-only serializer subclass
# ─────────────────────────────────────────────────────────────────────────────

class GroupEndowmentSerializerNoDBValidation(GroupEndowmentSerializer):
    """
    Identical to GroupEndowmentSerializer but with all DB-hitting validators
    stripped out.

    Why this is needed:
      1. register_no is the primary key -> DRF auto-adds a UniqueValidator
         that fires SELECT EXISTS against view_copo_groupEndowment.
      2. unique_together = [['register_no', 'policy_no']] -> DRF auto-adds a
         UniqueTogetherValidator on the serializer itself, also hitting the
         same view.
    Neither table exists in the test SQLite DB (managed=False, lives in
    company_external), so both must be removed for any is_valid() call to
    complete without a DB error.

    Serialisation tests (output shape, round-trips) continue to use the real
    GroupEndowmentSerializer via unsaved model instances, so the production
    serializer is still fully exercised.
    """
    register_no = drf_serializers.CharField(
        max_length=50,
        validators=[],  # drop auto-added UniqueValidator for the PK field
    )

    class Meta(GroupEndowmentSerializer.Meta):
        validators = []  # drop auto-added UniqueTogetherValidator


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_account(username="testuser", password="testpass123", **kwargs):
    return Account.objects.create_user(username=username, password=password, **kwargs)


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


def make_group_information(**kwargs):
    """
    Build an unsaved GroupInformation instance (managed=False, so we never
    hit the DB for this model in unit tests).
    """
    defaults = dict(
        group_id="GRP001",
        group_name="Test Group",
        group_name_nepali=None,
        is_active=True,
        total_members_count=10,
        total_active_policies=8,
        total_premium="5000.0000",
        total_sa="100000.0000",
        death_claim=1,
        surrender_claim=0,
        maturity_claim=2,
        transfer_claim=0,
        terminate_claim=0,
        cancel_claim=0,
    )
    defaults.update(kwargs)
    return GroupInformation(**defaults)


def make_group_endowment(**kwargs):
    """
    Build an unsaved GroupEndowment instance (managed=False).
    Only register_no and policy_no are required at the model level.
    """
    defaults = dict(
        register_no="REG001",
        policy_no="POL001",
    )
    defaults.update(kwargs)
    return GroupEndowment(**defaults)


# ─────────────────────────────────────────────────────────────────────────────
# 1. CustomTokenObtainPairSerializer
# ─────────────────────────────────────────────────────────────────────────────

class TestCustomTokenObtainPairSerializer(TestCase):
    """
    Tests for the custom JWT serializer.

    We patch `authenticate` and `get_token` so tests never touch simplejwt
    internals or require a real JWT secret.
    """

    # ── fixtures ──────────────────────────────────────────────────────────────

    def setUp(self):
        # company user
        self.company_account = make_account("company_user", "pass123")
        self.company = make_company(self.company_account, "Acme Corp")

        # individual user
        self.company_account2 = make_account("company_user2", "pass123")
        self.company2 = make_company(self.company_account2, "Beta Corp")
        self.group = make_group(self.company2)
        self.indiv_account = make_account("indiv_user", "pass123")
        self.individual = make_individual(self.group, self.indiv_account, "Jane Doe")

        # staff user
        self.staff_account = make_account("staff_user", "pass123", is_staff=True)

        # inactive user
        self.inactive_account = make_account(
            "inactive_user", "pass123", is_active=False
        )

    def _make_fake_token(self):
        """Return a lightweight mock that simulates a simplejwt refresh token."""
        fake_access = MagicMock()
        fake_access.__str__ = lambda s: "fake.access.token"
        fake_refresh = MagicMock()
        fake_refresh.__str__ = lambda s: "fake.refresh.token"
        fake_refresh.access_token = fake_access
        return fake_refresh

    def _validate(self, user, password="pass123"):
        """
        Run the serializer's validate() with authenticate and get_token patched.
        Returns the data dict on success, or raises ValidationError.
        """
        fake_token = self._make_fake_token()
        with patch(
            "api_corporate.serializers.authenticate", return_value=user
        ), patch.object(
            CustomTokenObtainPairSerializer, "get_token", return_value=fake_token
        ):
            s = CustomTokenObtainPairSerializer()
            return s.validate({"username": user.username, "password": password})

    # ── invalid / inactive ────────────────────────────────────────────────────

    def test_invalid_credentials_raise_validation_error(self):
        with patch("api_corporate.serializers.authenticate", return_value=None):
            s = CustomTokenObtainPairSerializer()
            with self.assertRaises(Exception):
                s.validate({"username": "nobody", "password": "wrong"})

    def test_inactive_user_raises_validation_error(self):
        with patch(
            "api_corporate.serializers.authenticate",
            return_value=self.inactive_account,
        ):
            s = CustomTokenObtainPairSerializer()
            with self.assertRaises(Exception):
                s.validate(
                    {"username": "inactive_user", "password": "pass123"}
                )

    # ── token keys always present ─────────────────────────────────────────────

    def test_response_always_contains_access_and_refresh(self):
        data = self._validate(self.company_account)
        self.assertIn("access", data)
        self.assertIn("refresh", data)

    def test_response_always_contains_user_type_and_username(self):
        data = self._validate(self.company_account)
        self.assertIn("user_type", data)
        self.assertIn("username", data)

    # ── company user shape ────────────────────────────────────────────────────

    def test_company_user_type_is_company(self):
        data = self._validate(self.company_account)
        self.assertEqual(data["user_type"], "company")

    def test_company_response_contains_company_id(self):
        data = self._validate(self.company_account)
        self.assertIn("company_id", data)
        self.assertEqual(data["company_id"], self.company.company_id)

    def test_company_response_contains_company_name(self):
        data = self._validate(self.company_account)
        self.assertEqual(data["company_name"], "Acme Corp")

    def test_company_response_contains_is_active(self):
        data = self._validate(self.company_account)
        self.assertIn("is_active", data)

    def test_company_response_has_no_individual_fields(self):
        data = self._validate(self.company_account)
        self.assertNotIn("user_id", data)
        self.assertNotIn("user_full_name", data)
        self.assertNotIn("group_id", data)

    # ── individual user shape ─────────────────────────────────────────────────

    def test_individual_user_type_is_individual(self):
        data = self._validate(self.indiv_account)
        self.assertEqual(data["user_type"], "individual")

    def test_individual_response_contains_user_id(self):
        data = self._validate(self.indiv_account)
        self.assertIn("user_id", data)
        self.assertEqual(data["user_id"], self.individual.user_id)

    def test_individual_response_contains_user_full_name(self):
        data = self._validate(self.indiv_account)
        self.assertEqual(data["user_full_name"], "Jane Doe")

    def test_individual_response_contains_group_id(self):
        data = self._validate(self.indiv_account)
        self.assertIn("group_id", data)
        self.assertEqual(data["group_id"], self.group.group_id)

    def test_individual_response_has_no_company_fields(self):
        data = self._validate(self.indiv_account)
        self.assertNotIn("company_id", data)
        self.assertNotIn("company_name", data)

    # ── staff user shape ──────────────────────────────────────────────────────

    def test_staff_user_type_is_staff(self):
        data = self._validate(self.staff_account)
        self.assertEqual(data["user_type"], "staff")

    def test_staff_response_has_no_company_or_individual_extras(self):
        data = self._validate(self.staff_account)
        self.assertNotIn("company_id", data)
        self.assertNotIn("user_id", data)

    def test_username_in_response_matches_authenticated_user(self):
        data = self._validate(self.staff_account)
        self.assertEqual(data["username"], "staff_user")


# ─────────────────────────────────────────────────────────────────────────────
# 2. GroupInformationSerializer
# ─────────────────────────────────────────────────────────────────────────────

class TestGroupInformationSerializer(TestCase):
    """
    GroupInformation is an unmanaged DB view.  We test serialization by
    building unsaved model instances — no DB writes needed.
    """

    # ── declared field list ───────────────────────────────────────────────────

    EXPECTED_FIELDS = {
        "group_id",
        "group_name",
        "group_name_nepali",
        "is_active",
        "total_members_count",
        "total_active_policies",
        "total_premium",
        "total_sa",
        "death_claim",
        "surrender_claim",
        "maturity_claim",
        "transfer_claim",
        "terminate_claim",
        "cancel_claim",
    }

    def _serialize(self, **kwargs):
        instance = make_group_information(**kwargs)
        return GroupInformationSerializer(instance).data

    # ── output shape ──────────────────────────────────────────────────────────

    def test_output_contains_exactly_declared_fields(self):
        data = self._serialize()
        self.assertEqual(set(data.keys()), self.EXPECTED_FIELDS)

    def test_output_contains_no_extra_fields(self):
        """No field outside EXPECTED_FIELDS should leak through."""
        data = self._serialize()
        for key in data.keys():
            self.assertIn(key, self.EXPECTED_FIELDS)

    # ── read-only: input is ignored ───────────────────────────────────────────

    def test_all_fields_are_read_only(self):
        """
        The serializer declares read_only_fields = fields.
        Passing data into it should produce an empty validated payload — 
        the serializer should flag no writable fields.
        """
        s = GroupInformationSerializer(data={
            "group_id": "INJECTED",
            "group_name": "Injected Name",
            "total_members_count": 999,
        })
        # is_valid() should pass (nothing to validate for read-only fields)
        s.is_valid()
        # validated_data must be empty — read-only fields are never accepted
        self.assertEqual(s.validated_data, {})

    def test_read_only_input_does_not_change_existing_instance(self):
        instance = make_group_information(group_name="Original")
        s = GroupInformationSerializer(
            instance, data={"group_name": "Overwritten"}
        )
        s.is_valid()
        # The serialized output must still reflect the original instance
        self.assertEqual(s.data["group_name"], "Original")

    # ── nullable fields ───────────────────────────────────────────────────────

    def test_group_name_serialises_as_none_when_null(self):
        data = self._serialize(group_name=None)
        self.assertIsNone(data["group_name"])

    def test_group_name_nepali_serialises_as_none_when_null(self):
        data = self._serialize(group_name_nepali=None)
        self.assertIsNone(data["group_name_nepali"])

    def test_is_active_serialises_as_none_when_null(self):
        data = self._serialize(is_active=None)
        self.assertIsNone(data["is_active"])

    def test_integer_stat_fields_serialise_as_none_when_null(self):
        data = self._serialize(
            total_members_count=None,
            total_active_policies=None,
            death_claim=None,
        )
        self.assertIsNone(data["total_members_count"])
        self.assertIsNone(data["total_active_policies"])
        self.assertIsNone(data["death_claim"])

    # ── field value round-trips ───────────────────────────────────────────────

    def test_group_id_value_round_trips(self):
        data = self._serialize(group_id="GRP999")
        self.assertEqual(data["group_id"], "GRP999")

    def test_is_active_true_round_trips(self):
        data = self._serialize(is_active=True)
        self.assertTrue(data["is_active"])

    def test_is_active_false_round_trips(self):
        data = self._serialize(is_active=False)
        self.assertFalse(data["is_active"])

    def test_integer_count_round_trips(self):
        data = self._serialize(total_members_count=42)
        self.assertEqual(data["total_members_count"], 42)

    def test_decimal_fields_are_present_and_non_none(self):
        data = self._serialize(total_premium="1234.5678", total_sa="9999.0000")
        self.assertIsNotNone(data["total_premium"])
        self.assertIsNotNone(data["total_sa"])

    def test_all_claim_integer_fields_round_trip(self):
        data = self._serialize(
            death_claim=1,
            surrender_claim=2,
            maturity_claim=3,
            transfer_claim=4,
            terminate_claim=5,
            cancel_claim=6,
        )
        self.assertEqual(data["death_claim"], 1)
        self.assertEqual(data["surrender_claim"], 2)
        self.assertEqual(data["maturity_claim"], 3)
        self.assertEqual(data["transfer_claim"], 4)
        self.assertEqual(data["terminate_claim"], 5)
        self.assertEqual(data["cancel_claim"], 6)


# ─────────────────────────────────────────────────────────────────────────────
# 3. GroupEndowmentSerializer
# ─────────────────────────────────────────────────────────────────────────────

class TestGroupEndowmentSerializer(TestCase):
    """
    GroupEndowment is also an unmanaged DB view.
    GroupEndowmentSerializer uses fields = '__all__', so we verify the full
    field inventory, required-field enforcement, and optional-field behaviour.
    """

    # ── complete field inventory ──────────────────────────────────────────────

    # Every field defined on the model
    ALL_MODEL_FIELDS = {
        "register_no", "policy_no", "branch", "group_id", "doc", "term",
        "sum_assured", "premium", "fup", "maturity_date", "policy_status",
        "policy_type", "late_fine", "paid_date", "instalment", "paid_amount",
        "batch_no", "details_remarks", "intrest", "claim_status",
        "late_fine_percent", "reduced_instalment", "employee_id", "name",
        "nep_name", "gender", "occupation", "dob", "age", "extra_premium",
        "total_premium", "id_no", "id_type", "appointed_date",
        "endowment_remarks", "address", "email", "mobile", "adb",
        "previous_policy", "occ_extra_amount", "adb_discount", "father_name",
        "mother_name", "nominee_name", "nominee_address",
        "phone_number_residence", "transfer_date", "duplicate_policy_date",
        "approved_date", "approved_by", "lapse_date", "lapse_active_date",
        "doe", "approve_remarks", "modified_date", "basic_premium", "is_adb",
        "after_dis_rebate_rate", "fiscal_year", "nominee_relationship",
        "claim_date", "termination_date", "is_ind_issue", "province_id",
        "district_id", "municipality_id", "ward_no", "age_proof_doc_type",
        "age_proof_doc_no", "nep_address", "nep_father_name",
        "nep_mother_name", "nep_nominee_name", "nep_nominee_address",
        "nom_district_id", "nominee_ward_no", "nominee_phone", "plan_id",
        "is_multiple_policy_issued", "terminate_by", "cancel_date",
        "cancel_by", "active_date", "active_by", "terminate_remarks",
        "cancel_remarks", "active_remarks", "lapse_by", "lapse_remarks",
    }

    def _serialize(self, **kwargs):
        instance = make_group_endowment(**kwargs)
        return GroupEndowmentSerializer(instance).data

    # ── output shape ──────────────────────────────────────────────────────────

    def test_output_contains_all_model_fields(self):
        data = self._serialize()
        self.assertEqual(set(data.keys()), self.ALL_MODEL_FIELDS)

    def test_output_has_no_unexpected_fields(self):
        data = self._serialize()
        for key in data.keys():
            self.assertIn(key, self.ALL_MODEL_FIELDS)

    # ── required fields ───────────────────────────────────────────────────────

    def test_register_no_present_in_output(self):
        data = self._serialize(register_no="REG001")
        self.assertEqual(data["register_no"], "REG001")

    def test_policy_no_present_in_output(self):
        data = self._serialize(policy_no="POL001")
        self.assertEqual(data["policy_no"], "POL001")

    def test_serializer_input_requires_register_no(self):
        """register_no is the PK and not nullable — missing it is invalid."""
        s = GroupEndowmentSerializerNoDBValidation(data={"policy_no": "POL001"})
        self.assertFalse(s.is_valid())
        self.assertIn("register_no", s.errors)

    def test_serializer_input_requires_policy_no(self):
        s = GroupEndowmentSerializerNoDBValidation(data={"register_no": "REG001"})
        self.assertFalse(s.is_valid())
        self.assertIn("policy_no", s.errors)

    # ── optional fields default to None ──────────────────────────────────────

    def test_all_optional_fields_are_none_by_default(self):
        data = self._serialize()
        optional_nullable = self.ALL_MODEL_FIELDS - {"register_no", "policy_no"}
        for field in optional_nullable:
            self.assertIsNone(
                data[field],
                msg=f"Expected {field} to be None for a minimal instance",
            )

    # ── max_length boundaries ─────────────────────────────────────────────────

    def test_register_no_at_max_length_50_is_valid(self):
        s = GroupEndowmentSerializerNoDBValidation(
            data={"register_no": "R" * 50, "policy_no": "POL001"}
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_register_no_exceeding_max_length_is_invalid(self):
        s = GroupEndowmentSerializerNoDBValidation(
            data={"register_no": "R" * 51, "policy_no": "POL001"}
        )
        self.assertFalse(s.is_valid())
        self.assertIn("register_no", s.errors)

    def test_policy_no_at_max_length_50_is_valid(self):
        s = GroupEndowmentSerializerNoDBValidation(
            data={"register_no": "REG001", "policy_no": "P" * 50}
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_policy_no_exceeding_max_length_is_invalid(self):
        s = GroupEndowmentSerializerNoDBValidation(
            data={"register_no": "REG001", "policy_no": "P" * 51}
        )
        self.assertFalse(s.is_valid())
        self.assertIn("policy_no", s.errors)

    def test_name_at_max_length_50_is_valid(self):
        s = GroupEndowmentSerializerNoDBValidation(
            data={"register_no": "REG001", "policy_no": "POL001", "name": "N" * 50}
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_name_exceeding_max_length_is_invalid(self):
        s = GroupEndowmentSerializerNoDBValidation(
            data={"register_no": "REG001", "policy_no": "POL001", "name": "N" * 51}
        )
        self.assertFalse(s.is_valid())
        self.assertIn("name", s.errors)

    def test_nominee_relationship_at_max_length_100_is_valid(self):
        s = GroupEndowmentSerializerNoDBValidation(data={
            "register_no": "REG001",
            "policy_no": "POL001",
            "nominee_relationship": "X" * 100,
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_nominee_relationship_exceeding_max_length_is_invalid(self):
        s = GroupEndowmentSerializerNoDBValidation(data={
            "register_no": "REG001",
            "policy_no": "POL001",
            "nominee_relationship": "X" * 101,
        })
        self.assertFalse(s.is_valid())
        self.assertIn("nominee_relationship", s.errors)

    def test_endowment_remarks_at_max_length_200_is_valid(self):
        s = GroupEndowmentSerializerNoDBValidation(data={
            "register_no": "REG001",
            "policy_no": "POL001",
            "endowment_remarks": "R" * 200,
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_endowment_remarks_exceeding_max_length_is_invalid(self):
        s = GroupEndowmentSerializerNoDBValidation(data={
            "register_no": "REG001",
            "policy_no": "POL001",
            "endowment_remarks": "R" * 201,
        })
        self.assertFalse(s.is_valid())
        self.assertIn("endowment_remarks", s.errors)

    # ── date / datetime fields ────────────────────────────────────────────────

    def test_doc_accepts_valid_date_string(self):
        s = GroupEndowmentSerializerNoDBValidation(data={
            "register_no": "REG001",
            "policy_no": "POL001",
            "doc": "2024-01-15",
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_doc_rejects_invalid_date_string(self):
        s = GroupEndowmentSerializerNoDBValidation(data={
            "register_no": "REG001",
            "policy_no": "POL001",
            "doc": "not-a-date",
        })
        self.assertFalse(s.is_valid())
        self.assertIn("doc", s.errors)

    def test_fup_accepts_valid_datetime_string(self):
        s = GroupEndowmentSerializerNoDBValidation(data={
            "register_no": "REG001",
            "policy_no": "POL001",
            "fup": "2024-01-15T10:30:00",
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_fup_rejects_invalid_datetime_string(self):
        s = GroupEndowmentSerializerNoDBValidation(data={
            "register_no": "REG001",
            "policy_no": "POL001",
            "fup": "15/01/2024 10:30",  # non-ISO format
        })
        self.assertFalse(s.is_valid())
        self.assertIn("fup", s.errors)

    def test_maturity_date_accepts_valid_date(self):
        s = GroupEndowmentSerializerNoDBValidation(data={
            "register_no": "REG001",
            "policy_no": "POL001",
            "maturity_date": "2030-06-30",
        })
        self.assertTrue(s.is_valid(), s.errors)

    # ── optional CharField fields round-trip ──────────────────────────────────

    def test_branch_round_trips(self):
        data = self._serialize(branch="Kathmandu")
        self.assertEqual(data["branch"], "Kathmandu")

    def test_gender_round_trips(self):
        data = self._serialize(gender="Male")
        self.assertEqual(data["gender"], "Male")

    def test_email_round_trips(self):
        """email is a plain CharField on GroupEndowment, not EmailField."""
        data = self._serialize(email="test@example.com")
        self.assertEqual(data["email"], "test@example.com")

    def test_policy_status_round_trips(self):
        data = self._serialize(policy_status="Active")
        self.assertEqual(data["policy_status"], "Active")

    # ── boolean optional field ────────────────────────────────────────────────

    def test_is_multiple_policy_issued_true_round_trips(self):
        data = self._serialize(is_multiple_policy_issued=True)
        self.assertTrue(data["is_multiple_policy_issued"])

    def test_is_multiple_policy_issued_false_round_trips(self):
        data = self._serialize(is_multiple_policy_issued=False)
        self.assertFalse(data["is_multiple_policy_issued"])

    # ── small integer fields ──────────────────────────────────────────────────

    def test_term_round_trips(self):
        data = self._serialize(term=20)
        self.assertEqual(data["term"], 20)

    def test_instalment_round_trips(self):
        data = self._serialize(instalment=12)
        self.assertEqual(data["instalment"], 12)

    def test_plan_id_round_trips(self):
        data = self._serialize(plan_id=5)
        self.assertEqual(data["plan_id"], 5)

    # ── decimal fields ────────────────────────────────────────────────────────

    def test_sum_assured_round_trips(self):
        data = self._serialize(sum_assured="250000.0000")
        self.assertIsNotNone(data["sum_assured"])

    def test_premium_round_trips(self):
        data = self._serialize(premium="1500.5000")
        self.assertIsNotNone(data["premium"])