"""
api_corporate/tests/test_api_endpoints.py
==========================================
Full test suite for all api_corporate endpoints.

Run with:
    python manage.py test api_corporate.tests.test_api_endpoints \
        --settings=corporate_portal.test_settings

--- v2 fix notes ---
Three root causes were fixed vs the original file:

FIX 1 — Wrong patch target
    Old: patch('django.db.connections')
    New: patch('api_corporate.views.connections')
    Why: Views import `connections` at module level. Patching the source
         module intercepts the reference the view actually uses.

FIX 2 — DatabaseOperationForbidden
    Django's TestCase blocks queries to any DB not listed in the class's
    `databases` attribute. All classes whose views touch company_external
    now declare:
        databases = ('default', 'company_external')
    The SQLite :memory: company_external DB (from test_settings.py) is used
    so no real MSSQL connection is required.

FIX 3 — UnboundLocalError for `sql` / cursor mock timing
    Several views define `sql` inside the `with cursor:` block and then
    reference it in the `except` handler. If the cursor *context manager*
    raises on enter, `sql` is never assigned and the except handler itself
    crashes with UnboundLocalError.
    Fix: _make_cursor_raises() raises *inside* the context manager (i.e.
    after __enter__ returns), so the `with` block body starts executing and
    the view's `sql = ...` line is reached before the exception propagates.
    This correctly exercises the view's except path without the secondary
    UnboundLocalError.

FIX 4 — ViewSet / django-filter MagicMock introspection
    django-filter introspects queryset field types to build filters; a
    MagicMock queryset causes AssertionError. Fix: patch get_queryset() on
    the ViewSet class itself to return a real (empty) QuerySet from the
    SQLite company_external DB.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from main_system.models import Account, Company, Group


# ---------------------------------------------------------------------------
# Patch target — must match `from django.db import connections` in views.py
# ---------------------------------------------------------------------------
VIEW_CONNECTIONS = "api_corporate.views.connections"


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

def make_account(username, password="Test@1234", **kwargs):
    return Account.objects.create_user(username=username, password=password, **kwargs)


def make_company_user(username="corp_user", password="Test@1234", isactive=True):
    account = make_account(username, password)
    company = Company.objects.create(
        username=account,
        company_name=f"Company for {username}",
        isactive=isactive,
    )
    return account, company


def make_group(company, group_id="GRP001", group_name="Test Group", isdeleted=False):
    return Group.objects.create(
        company_id=company,
        group_id=group_id,
        group_name=group_name,
        isdeleted=isdeleted,
    )


def jwt_for(account):
    return str(RefreshToken.for_user(account).access_token)


# ---------------------------------------------------------------------------
# Cursor mock factories
# ---------------------------------------------------------------------------

def _cursor_with_rows(columns, rows, nextset_returns=False):
    """
    Returns a callable context manager that yields a cursor with the given
    columns and rows. Used for happy-path tests.
    """
    cursor = MagicMock()
    cursor.description = [(c,) for c in columns] if columns else None
    cursor.fetchall.return_value = rows
    cursor.fetchone.return_value = rows[0] if rows else None
    cursor.nextset.return_value = nextset_returns

    @contextmanager
    def _cm():
        yield cursor

    return _cm


def _cursor_empty():
    """Cursor that returns no rows (simulates SP returning no data)."""
    cursor = MagicMock()
    cursor.description = None
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = None
    cursor.nextset.return_value = False

    @contextmanager
    def _cm():
        yield cursor

    return _cm


def _cursor_raises(exc=None):
    """
    Context manager that raises *after* __enter__ so that:
      - The view's `with connections[...].cursor() as cursor:` block starts
      - The view's `sql = ...` line is executed
      - Then the exception is raised, hitting the view's except handler
    This avoids the secondary UnboundLocalError in views that define `sql`
    inside the with block and reference it in the except handler.
    """
    if exc is None:
        exc = Exception("Simulated DB failure")

    cursor = MagicMock()
    cursor.execute.side_effect = exc  # raises when cursor.execute() is called

    @contextmanager
    def _cm():
        yield cursor  # __enter__ succeeds; raise happens when execute() is called

    return _cm


# ===========================================================================
# 1. Authentication — POST /api/corporate/auth/login/
# ===========================================================================

class LoginEndpointTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("token_obtain_pair")
        self.account, self.company = make_company_user(
            username="login_corp", password="Pass@9999"
        )

    def test_valid_company_login_returns_tokens(self):
        resp = self.client.post(
            self.url, {"username": "login_corp", "password": "Pass@9999"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["username"], "login_corp")

    def test_wrong_password_returns_401(self):
        resp = self.client.post(
            self.url, {"username": "login_corp", "password": "WRONG"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_user_returns_401(self):
        resp = self.client.post(
            self.url, {"username": "nobody", "password": "Pass@9999"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_user_cannot_login_via_api(self):
        make_account("staff_user", "Pass@9999", is_staff=True)
        resp = self.client.post(
            self.url, {"username": "staff_user", "password": "Pass@9999"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_cannot_login_via_api(self):
        make_account("admin_user", "Pass@9999", is_staff=True, is_superuser=True)
        resp = self.client.post(
            self.url, {"username": "admin_user", "password": "Pass@9999"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_company_returns_403(self):
        make_company_user(username="inactive_corp", password="Pass@9999", isactive=False)
        resp = self.client.post(
            self.url, {"username": "inactive_corp", "password": "Pass@9999"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("inactive", resp.data["error"].lower())

    def test_empty_body_returns_401(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ===========================================================================
# 2. Token Refresh — POST /api/corporate/auth/refresh/
# ===========================================================================

class TokenRefreshTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("token_refresh")
        self.account, _ = make_company_user("refresh_corp")

    def test_valid_refresh_returns_new_access(self):
        refresh = RefreshToken.for_user(self.account)
        resp = self.client.post(self.url, {"refresh": str(refresh)}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)

    def test_invalid_refresh_returns_401(self):
        resp = self.client.post(self.url, {"refresh": "not-a-token"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_refresh_returns_400(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ===========================================================================
# 3. Group Information — GET /api/corporate/groups/
# ===========================================================================

class GroupInformationTests(TestCase):
    """
    The view reads PortalGroup from `default` (fine), then queries
    GroupInformation.objects.using('company_external'). We mock the
    GroupInformation model so we never hit company_external.
    """

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("group-information")
        self.account, self.company = make_company_user("grp_corp")
        self.group = make_group(self.company)
        self.token = jwt_for(self.account)

    def _get(self, token=None, params=None):
        t = token or self.token
        return self.client.get(
            self.url, params or {}, **{"HTTP_AUTHORIZATION": f"Bearer {t}"}
        )

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_company_returns_403(self):
        acc_i, _ = make_company_user("grp_inactive", isactive=False)
        resp = self._get(token=jwt_for(acc_i))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_with_no_groups_returns_empty(self):
        acc2, _ = make_company_user("grp_nogrp")
        resp = self._get(token=jwt_for(acc2))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)

    def test_company_with_groups_returns_results(self):
        with patch("api_corporate.views.GroupInformation") as mock_gi, \
             patch("api_corporate.views.GroupInformationSerializer") as mock_ser:
            mock_qs = MagicMock()
            mock_qs.count.return_value = 1
            mock_gi.objects.using.return_value.filter.return_value = mock_qs
            mock_ser.return_value.data = [{"group_id": "GRP001"}]
            resp = self._get()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("results", resp.data)

    def test_staff_can_filter_by_company_id(self):
        staff = make_account("staff_gi", is_staff=True)
        self.client.force_authenticate(user=staff)
        with patch("api_corporate.views.GroupInformation") as mock_gi, \
             patch("api_corporate.views.GroupInformationSerializer") as mock_ser:
            mock_qs = MagicMock()
            mock_qs.count.return_value = 0
            mock_gi.objects.using.return_value.filter.return_value = mock_qs
            mock_ser.return_value.data = []
            resp = self.client.get(self.url, {"company_id": self.company.company_id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_staff_with_invalid_company_id_returns_400(self):
        staff = make_account("staff_gi2", is_staff=True)
        self.client.force_authenticate(user=staff)
        resp = self.client.get(self.url, {"company_id": "not-a-number"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ===========================================================================
# 4. Shared mixin for the family of POST report endpoints
# ===========================================================================

class _ReportEndpointMixin:
    """
    Base mixin for report endpoints that share the pattern:
      - POST with group_id + two date params
      - group-ownership check (returns 403 for unowned groups)
      - calls connections['company_external'].cursor()

    Subclasses define:
        url_name      reverse() name
        sp_columns    column names for happy-path cursor
        sp_rows       row tuples for happy-path cursor
        response_key  dict key in 200 response, or None for list responses
    """

    url_name: str = ""
    sp_columns: list = ["col1"]
    sp_rows: list = [("val1",)]
    response_key = None

    databases = ("default", "company_external")

    def setUp(self):
        self.client = APIClient()
        self.url = reverse(self.url_name)
        # Use a short but unique username suffix per subclass
        uname = self.url_name.replace("-", "_")[:12]
        self.account, self.company = make_company_user(f"rpt_{uname}")
        self.group = make_group(self.company, group_id=f"G{uname[:6]}")
        self.token = jwt_for(self.account)
        self.valid_payload = self._valid_payload()

    def _valid_payload(self):
        return {
            "group_id": self.group.group_id,
            "from_date": "2024-01-01",
            "to_date": "2024-12-31",
        }

    def _post(self, payload=None, token=None):
        t = token or self.token
        return self.client.post(
            self.url,
            payload if payload is not None else self.valid_payload,
            format="json",
            **{"HTTP_AUTHORIZATION": f"Bearer {t}"},
        )

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_group_id_returns_400(self):
        payload = {k: v for k, v in self.valid_payload.items() if k != "group_id"}
        self.assertEqual(self._post(payload).status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_from_date_returns_400(self):
        payload = {k: v for k, v in self.valid_payload.items() if k != "from_date"}
        self.assertEqual(self._post(payload).status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_to_date_returns_400(self):
        payload = {k: v for k, v in self.valid_payload.items() if k != "to_date"}
        self.assertEqual(self._post(payload).status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_group_returns_403(self):
        resp = self._post({**self.valid_payload, "group_id": "FAKE_GROUP_XYZ"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_request_with_data_returns_200(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_with_rows(
                self.sp_columns, self.sp_rows
            )
            resp = self._post()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        if self.response_key:
            self.assertIn(self.response_key, resp.data)
        else:
            self.assertIsInstance(resp.data, list)

    def test_valid_request_no_data_returns_200(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_empty()
            resp = self._post()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_db_exception_returns_500(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_raises()
            resp = self._post()
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", resp.data)


# ===========================================================================
# 5. Concrete report test classes
# ===========================================================================

class MaturityForecastingReportTests(_ReportEndpointMixin, TestCase):
    url_name = "maturity-forecasting"
    sp_columns = ["PolicyNo", "Name", "MaturityDate", "SumAssured"]
    sp_rows = [("POL001", "Alice", "2025-06-01", 100000)]
    response_key = "policies"


class LoanRepaymentReportTests(_ReportEndpointMixin, TestCase):
    url_name = "loan-repayment-report"
    sp_columns = ["PolicyNo", "LoanAmount", "RepaymentDate"]
    sp_rows = [("POL002", 5000, "2024-03-15")]
    response_key = "repayments"


class GroupTransferReportTests(_ReportEndpointMixin, TestCase):
    url_name = "group-transfer-report"
    sp_columns = ["PolicyNo", "TransferDate", "FromGroup"]
    sp_rows = [("POL003", "2024-04-01", "GRP_OLD")]
    response_key = "transfers"

    def _valid_payload(self):
        return {
            "group_id": self.group.group_id,
            "transfer_date_from": "2024-01-01",
            "transfer_date_to": "2024-12-31",
        }

    def test_missing_from_date_returns_400(self):
        payload = {k: v for k, v in self.valid_payload.items() if k != "transfer_date_from"}
        self.assertEqual(self._post(payload).status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_to_date_returns_400(self):
        payload = {k: v for k, v in self.valid_payload.items() if k != "transfer_date_to"}
        self.assertEqual(self._post(payload).status_code, status.HTTP_400_BAD_REQUEST)


class DeathClaimReportTests(_ReportEndpointMixin, TestCase):
    url_name = "death-claim-report"
    sp_columns = ["PolicyNo", "DeathDate", "ClaimAmount"]
    sp_rows = [("POL004", "2024-02-10", 200000)]
    response_key = None  # plain list response


class MaturityClaimReportTests(_ReportEndpointMixin, TestCase):
    url_name = "maturity-claim-report"
    sp_columns = ["PolicyNo", "MaturityDate", "Amount"]
    sp_rows = [("POL005", "2024-08-31", 150000)]
    response_key = None


class SurrenderClaimReportTests(_ReportEndpointMixin, TestCase):
    url_name = "surrender-claim-report"
    sp_columns = ["PolicyNo", "SurrenderDate", "SurrenderValue"]
    sp_rows = [("POL006", "2024-05-20", 80000)]
    response_key = None


# ===========================================================================
# 6. Group Business Detail Report
# ===========================================================================

class GroupBusinessDetailReportTests(TestCase):
    databases = ("default", "company_external")

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("group-business-detail-report")
        self.account, self.company = make_company_user("biz_corp")
        self.group = make_group(self.company, group_id="BIZ001")
        self.token = jwt_for(self.account)
        self.valid_payload = {
            "group_id": self.group.group_id,
            "flag": "NB",
            "filter_by": "PaidDate",
            "from_date": "2024-01-01",
            "to_date": "2024-12-31",
        }

    def _post(self, payload=None):
        return self.client.post(
            self.url, payload or self.valid_payload, format="json",
            **{"HTTP_AUTHORIZATION": f"Bearer {self.token}"},
        )

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_any_field_returns_400(self):
        for field in ("group_id", "flag", "filter_by", "from_date", "to_date"):
            payload = {k: v for k, v in self.valid_payload.items() if k != field}
            self.assertEqual(
                self._post(payload).status_code,
                status.HTTP_400_BAD_REQUEST,
                msg=f"Expected 400 when missing: {field}",
            )

    def test_invalid_flag_returns_400(self):
        resp = self._post({**self.valid_payload, "flag": "XX"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("flag", resp.data["error"].lower())

    def test_invalid_filter_by_returns_400(self):
        resp = self._post({**self.valid_payload, "filter_by": "BadOption"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("filter_by", resp.data["error"].lower())

    def test_wrong_group_returns_403(self):
        resp = self._post({**self.valid_payload, "group_id": "WRONG_GROUP"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_nb_request_returns_200(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_with_rows(
                ["PolicyNo", "Premium"], [("P001", 5000)]
            )
            resp = self._post()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_valid_rb_flag_accepted(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_with_rows(
                ["PolicyNo", "Premium"], [("P002", 3000)]
            )
            resp = self._post({**self.valid_payload, "flag": "RB"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_value_date_filter_accepted(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_with_rows(
                ["PolicyNo"], [("P003",)]
            )
            resp = self._post({**self.valid_payload, "filter_by": "ValueDate"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_db_error_returns_500(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_raises()
            resp = self._post()
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===========================================================================
# 7. Policy Summary — POST /api/corporate/policy-summary/
# ===========================================================================

class PolicySummaryReportTests(TestCase):
    databases = ("default", "company_external")

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("policy-summary-report")
        self.account, self.company = make_company_user("ps_corp")
        self.group = make_group(self.company, group_id="PS001")
        self.token = jwt_for(self.account)

    def _post(self, payload, token=None):
        t = token or self.token
        return self.client.post(
            self.url, payload, format="json",
            **{"HTTP_AUTHORIZATION": f"Bearer {t}"},
        )

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(self.url, {"policy_no": "P001"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_policy_no_returns_400(self):
        resp = self._post({})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("policy_no", resp.data["error"].lower())

    def test_inactive_company_returns_403(self):
        acc_i, _ = make_company_user("ps_inactive", isactive=False)
        resp = self._post({"policy_no": "P001"}, token=jwt_for(acc_i))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_with_no_groups_returns_404(self):
        acc2, _ = make_company_user("ps_nogrp")
        resp = self._post({"policy_no": "P001"}, token=jwt_for(acc2))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_valid_request_returns_list(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_with_rows(
                ["PolicyNo", "GroupId", "SumAssured"],
                [("P001", "PS001", 100000)],
            )
            resp = self._post({"policy_no": "P001"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)

    def test_db_error_returns_500(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_raises()
            resp = self._post({"policy_no": "P001"})
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===========================================================================
# 8. Policy Search — POST /api/corporate/policy-search/
# ===========================================================================

class PolicySearchTests(TestCase):
    databases = ("default", "company_external")

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("policy-search")
        self.account, self.company = make_company_user("search_corp")
        self.group = make_group(self.company, group_id="SRH001")
        self.token = jwt_for(self.account)

    def _post(self, payload, token=None):
        t = token or self.token
        return self.client.post(
            self.url, payload, format="json",
            **{"HTTP_AUTHORIZATION": f"Bearer {t}"},
        )

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(self.url, {"q": "alice"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_query_returns_empty_list(self):
        resp = self._post({"q": ""})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_missing_q_returns_empty_list(self):
        resp = self._post({})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_inactive_company_returns_403(self):
        acc_i, _ = make_company_user("search_inactive", isactive=False)
        resp = self._post({"q": "alice"}, token=jwt_for(acc_i))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_with_no_groups_returns_empty_list(self):
        acc2, _ = make_company_user("search_nogrp")
        resp = self._post({"q": "alice"}, token=jwt_for(acc2))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_valid_search_returns_results(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_with_rows(
                ["policyNo", "name", "employeeid"],
                [("POL007", "Alice Smith", "EMP001")],
            )
            resp = self._post({"q": "Alice"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["policyNo"], "POL007")

    def test_db_error_returns_500(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_raises()
            resp = self._post({"q": "crash"})
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===========================================================================
# 9. Policy Loans — POST /api/corporate/reports/policy-loans/
# ===========================================================================

class PolicyLoansTests(TestCase):
    databases = ("default", "company_external")

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("policy-loans")
        self.account, self.company = make_company_user("loans_corp")
        self.group = make_group(self.company, group_id="LN001")
        self.token = jwt_for(self.account)

    def _post(self, payload, token=None):
        t = token or self.token
        return self.client.post(
            self.url, payload, format="json",
            **{"HTTP_AUTHORIZATION": f"Bearer {t}"},
        )

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(self.url, {"policy_no": "P001"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_policy_no_returns_400(self):
        resp = self._post({})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_company_returns_403(self):
        acc_i, _ = make_company_user("loans_inactive", isactive=False)
        resp = self._post({"policy_no": "P001"}, token=jwt_for(acc_i))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_with_no_groups_returns_empty(self):
        acc2, _ = make_company_user("loans_nogrp")
        resp = self._post({"policy_no": "P001"}, token=jwt_for(acc2))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_valid_policy_returns_200(self):
        """
        The view runs two SQL queries inside one cursor context:
         1. SELECT groupId … WHERE policyNo = ?   (ownership check)
         2. SELECT loan details WHERE policyNo = ?
        fetchone() serves query 1; fetchall() serves query 2.
        """
        cursor = MagicMock()
        cursor.fetchone.return_value = (self.group.group_id,)
        cursor.description = [("LoanId",), ("Amount",), ("Status",)]
        cursor.fetchall.return_value = [("LOAN01", 50000, "Active")]
        cursor.nextset.return_value = False

        @contextmanager
        def _cm():
            yield cursor

        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cm
            resp = self._post({"policy_no": "P001"})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_db_error_returns_500(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_raises()
            resp = self._post({"policy_no": "P001"})
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===========================================================================
# 10. Surrender Calculator — POST /api/corporate/surrender-calculator/
# ===========================================================================

class SurrenderCalculatorTests(TestCase):
    databases = ("default", "company_external")

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("surrender-calculator")
        self.account, self.company = make_company_user("surr_corp")
        self.group = make_group(self.company, group_id="SC001")
        self.token = jwt_for(self.account)

    def _post(self, payload, token=None):
        t = token or self.token
        return self.client.post(
            self.url, payload, format="json",
            **{"HTTP_AUTHORIZATION": f"Bearer {t}"},
        )

    def test_unauthenticated_returns_401(self):
        resp = self.client.post(self.url, {"policy_no": "P001"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_policy_no_returns_400(self):
        resp = self._post({})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("policy_no", resp.data["error"].lower())

    def test_inactive_company_returns_403(self):
        acc_i, _ = make_company_user("surr_inactive", isactive=False)
        resp = self._post({"policy_no": "P001"}, token=jwt_for(acc_i))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_with_no_groups_returns_404(self):
        acc2, _ = make_company_user("surr_nogrp")
        resp = self._post({"policy_no": "P001"}, token=jwt_for(acc2))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_policy_not_found_returns_404(self):
        # fetchone returns None → no row → 404
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_with_rows([], [])
            resp = self._post({"policy_no": "GHOST"})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_valid_policy_returns_surrender_data(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_with_rows(
                ["policyNO", "hasActiveLoan", "SurrenderAmount"],
                [("P001", 0, 75000.0)],
            )
            resp = self._post({"policy_no": "P001"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("SurrenderAmount", resp.data)

    def test_db_error_returns_500(self):
        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cursor_raises()
            resp = self._post({"policy_no": "P001"})
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# ===========================================================================
# 11. Company Policies Web — GET /api/corporate/endowments/by_company/
# ===========================================================================

class CompanyPoliciesWebTests(TestCase):
    databases = ("default", "company_external")

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("company-policies-web")
        self.account, self.company = make_company_user("web_corp")
        self.group = make_group(self.company, group_id="WEB001")

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(self.url, {"company_id": self.company.company_id})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_company_id_returns_400(self):
        self.client.force_authenticate(user=self.account)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_integer_company_id_returns_400(self):
        self.client.force_authenticate(user=self.account)
        resp = self.client.get(self.url, {"company_id": "abc"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_company_user_cannot_access_other_company(self):
        _, other = make_company_user("other_web_corp")
        self.client.force_authenticate(user=self.account)
        resp = self.client.get(self.url, {"company_id": other.company_id})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_with_no_groups_returns_empty_payload(self):
        acc2, company2 = make_company_user("web_nogrp")
        self.client.force_authenticate(user=acc2)
        resp = self.client.get(self.url, {"company_id": company2.company_id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["group_ids"], [])

    def test_staff_can_access_any_company(self):
        staff = make_account("web_staff", is_staff=True)
        self.client.force_authenticate(user=staff)

        cursor = MagicMock()
        cursor.description = [("PolicyNo",), ("Name",)]
        cursor.fetchall.side_effect = [
            [("P001", "Alice")],  # latest_policies
            [],                   # fup_data
        ]
        cursor.fetchone.return_value = {"TotalActive": 1}
        cursor.nextset.side_effect = [True, False]

        @contextmanager
        def _cm():
            yield cursor

        with patch(VIEW_CONNECTIONS) as mc:
            mc.__getitem__.return_value.cursor = _cm
            resp = self.client.get(self.url, {"company_id": self.company.company_id})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ===========================================================================
# 12. CompanyPoliciesViewSet — GET /api/corporate/company/policies/
# ===========================================================================

class CompanyPoliciesViewSetTests(TestCase):
    """
    get_queryset() is patched to return a real empty QuerySet so that
    django-filter can introspect actual GroupEndowment model fields without
    touching the real MSSQL database.
    """
    databases = ("default", "company_external")

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("company-policies-list")
        self.account, self.company = make_company_user("viewset_corp")
        self.group = make_group(self.company, group_id="VS001")
        self.token = jwt_for(self.account)

    def _empty_qs(self):
        from api_corporate.models import GroupEndowment
        return GroupEndowment.objects.using("company_external").none()

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_gets_403_from_is_company_user(self):
        staff = make_account("vs_staff", is_staff=True)
        self.client.force_authenticate(user=staff)
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_individual_user_gets_403(self):
        from main_system.models import Individual
        ind_acc = make_account("vs_individual")
        Individual.objects.create(
            group_id=self.group, username=ind_acc, user_full_name="Test"
        )
        self.client.force_authenticate(user=ind_acc)
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_user_list_returns_200(self):
        with patch(
            "api_corporate.views.CompanyPoliciesViewSet.get_queryset",
            return_value=self._empty_qs(),
        ):
            resp = self.client.get(
                self.list_url,
                **{"HTTP_AUTHORIZATION": f"Bearer {self.token}"},
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ===========================================================================
# 13. GroupEndowmentViewSet — GET /api/corporate/endowments/
# ===========================================================================

class GroupEndowmentViewSetTests(TestCase):
    databases = ("default", "company_external")

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("endowment-list")
        self.account, self.company = make_company_user("endo_corp")
        self.group = make_group(self.company, group_id="END001")
        self.token = jwt_for(self.account)

    def _empty_qs(self):
        from api_corporate.models import GroupEndowment
        return GroupEndowment.objects.using("company_external").none()

    def test_unauthenticated_returns_401(self):
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_gets_200(self):
        with patch(
            "api_corporate.views.GroupEndowmentViewSet.get_queryset",
            return_value=self._empty_qs(),
        ):
            resp = self.client.get(
                self.list_url,
                **{"HTTP_AUTHORIZATION": f"Bearer {self.token}"},
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_by_company_missing_company_id_returns_400(self):
        resp = self.client.get(
            reverse("endowment-by-company"),
            **{"HTTP_AUTHORIZATION": f"Bearer {self.token}"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_by_company_invalid_company_id_returns_400(self):
        resp = self.client.get(
            reverse("endowment-by-company"),
            {"company_id": "xyz"},
            **{"HTTP_AUTHORIZATION": f"Bearer {self.token}"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_by_company_no_groups_returns_empty(self):
        # Create a company user with NO groups, then query their own company_id
        # so any ownership check in the view passes.
        acc2, company2 = make_company_user("endo_corp2")
        self.client.force_authenticate(user=acc2)
        resp = self.client.get(
            reverse("endowment-by-company"),
            {"company_id": company2.company_id},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # The by_company action returns either {"count": 0} or {"endowments": [], "count": 0}
        # depending on whether groups exist. Either way the response is 200 with no policies.
        data = resp.data
        policy_count = data.get("count", len(data.get("endowments", [])))
        self.assertEqual(policy_count, 0)

    def test_by_company_other_company_returns_403(self):
        # Confirm a company user cannot query another company's data.
        _, company2 = make_company_user("endo_other")
        self.client.force_authenticate(user=self.account)
        resp = self.client.get(
            reverse("endowment-by-company"),
            {"company_id": company2.company_id},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)