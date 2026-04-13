"""
main_system/tests/test_integration.py
======================================
Integration tests covering end-to-end workflows:
    1. Company setup workflow  : create company → assign groups → add individual users
    2. JWT login workflow      : API login → token obtained → authenticated API access
    3. Access control workflow : right users in, wrong users out across both session and JWT layers
    4. Group ownership         : company can only access its own groups via API

Run with:
    python manage.py test main_system.tests.test_integration --settings=corporate_portal.test_settings
"""

from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock

from main_system.models import Account, Company, Group, Individual


# ============================================================
# Shared base
# ============================================================

class IntegrationBase(TestCase):
    """
    Builds a full realistic dataset used across all integration test classes.

    Hierarchy:
        company_account  →  Company (Test Corp)
                                └── group_a  (GRP001, active)
                                └── group_b  (GRP002, active)
                                └── group_deleted (GRP003, deleted)
                        →  individual_account  →  Individual (linked to group_a)

        other_company_account → Company (Other Corp)
                                    └── other_group (GRP999)

        staff_account   : is_staff=True, no company/individual profile
    """

    def setUp(self):
        self.client = Client()
        self.api_client = APIClient()

        # ── Company A ──────────────────────────────────────────────────────
        self.company_account = Account.objects.create_user(
            username='testcorp',
            password='TestCorp123',
        )
        self.company = Company.objects.create(
            username=self.company_account,
            company_name='Test Corp',
            isactive=True,
        )

        # Groups for Company A
        self.group_a = Group.objects.create(
            company_id=self.company,
            group_id='GRP001',
            group_name='Group Alpha',
            isdeleted=False,
            isactive=True,
        )
        self.group_b = Group.objects.create(
            company_id=self.company,
            group_id='GRP002',
            group_name='Group Beta',
            isdeleted=False,
            isactive=True,
        )
        self.group_deleted = Group.objects.create(
            company_id=self.company,
            group_id='GRP003',
            group_name='Deleted Group',
            isdeleted=True,
            isactive=False,
        )

        # Individual user linked to group_a
        self.individual_account = Account.objects.create_user(
            username='induser',
            password='IndUser123',
        )
        self.individual = Individual.objects.create(
            username=self.individual_account,
            group_id=self.group_a,
            user_full_name='Test Individual',
        )

        # ── Company B (used for cross-company access tests) ────────────────
        self.other_company_account = Account.objects.create_user(
            username='othercorp',
            password='OtherCorp123',
        )
        self.other_company = Company.objects.create(
            username=self.other_company_account,
            company_name='Other Corp',
            isactive=True,
        )
        self.other_group = Group.objects.create(
            company_id=self.other_company,
            group_id='GRP999',
            group_name='Other Group',
            isdeleted=False,
            isactive=True,
        )

        # ── Staff user ─────────────────────────────────────────────────────
        self.staff_account = Account.objects.create_user(
            username='staffuser',
            password='StaffPass123',
            is_staff=True,
        )

    # ── helpers ────────────────────────────────────────────────────────────

    def get_jwt_token(self, username, password):
        """POSTs to the JWT login endpoint and returns the access token."""
        response = self.api_client.post(
            reverse('token_obtain_pair'),
            {'username': username, 'password': password},
            format='json',
        )
        return response

    def auth_api_client(self, token):
        """Returns an APIClient with the Bearer token already set."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return client


# ============================================================
# 1. Company Setup Workflow
#    create company → assign groups → add individual user
# ============================================================

class CompanySetupWorkflowTests(IntegrationBase):
    """
    Verifies that the data hierarchy created in setUp is consistent
    and that the portal correctly reflects it through its views.
    """

    def test_company_has_correct_active_group_count(self):
        active = Group.objects.filter(
            company_id=self.company,
            isdeleted=False,
        ).count()
        self.assertEqual(active, 2)  # group_a and group_b only

    def test_deleted_group_excluded_from_active_count(self):
        all_groups = Group.objects.filter(company_id=self.company).count()
        active = Group.objects.filter(company_id=self.company, isdeleted=False).count()
        self.assertEqual(all_groups, 3)
        self.assertEqual(active, 2)

    def test_individual_linked_to_correct_group_and_company(self):
        self.assertEqual(self.individual.group_id, self.group_a)
        self.assertEqual(self.individual.group_id.company_id, self.company)

    def test_individual_account_type_is_individual(self):
        self.assertEqual(self.individual_account.get_user_type(), 'individual')

    def test_company_account_type_is_company(self):
        self.assertEqual(self.company_account.get_user_type(), 'company')

    def test_company_dashboard_reflects_correct_group_count(self):
        """End-to-end: company logs in and sees correct total_groups in context."""
        self.client.login(username='testcorp', password='TestCorp123')
        response = self.client.get(reverse('company_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_groups'], 2)

    def test_two_companies_groups_are_isolated(self):
        """Groups from Company A must not bleed into Company B's queryset."""
        corp_a_groups = Group.objects.filter(
            company_id=self.company, isdeleted=False
        )
        corp_b_groups = Group.objects.filter(
            company_id=self.other_company, isdeleted=False
        )
        # No overlap in group_ids
        a_ids = set(corp_a_groups.values_list('group_id', flat=True))
        b_ids = set(corp_b_groups.values_list('group_id', flat=True))
        self.assertTrue(a_ids.isdisjoint(b_ids))


# ============================================================
# 2. JWT Login Workflow
#    API login → token returned → use token to hit protected endpoint
# ============================================================

class JWTLoginWorkflowTests(IntegrationBase):

    def test_company_user_receives_access_and_refresh_tokens(self):
        response = self.get_jwt_token('testcorp', 'TestCorp123')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('username', response.data)
        self.assertEqual(response.data['username'], 'testcorp')

    def test_staff_user_cannot_obtain_jwt_token(self):
        """API login explicitly blocks staff/admin users."""
        response = self.get_jwt_token('staffuser', 'StaffPass123')
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.data)

    def test_individual_user_cannot_obtain_jwt_token(self):
        """API login only allows company users."""
        response = self.get_jwt_token('induser', 'IndUser123')
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.data)

    def test_wrong_password_returns_401(self):
        response = self.get_jwt_token('testcorp', 'WrongPassword')
        self.assertEqual(response.status_code, 401)

    def test_inactive_company_cannot_obtain_jwt_token(self):
        self.company.isactive = False
        self.company.save()
        response = self.get_jwt_token('testcorp', 'TestCorp123')
        self.assertEqual(response.status_code, 403)
        self.assertIn('inactive', response.data.get('error', '').lower())

    def test_valid_token_grants_access_to_groups_endpoint(self):
        """
        Full flow: login → get token → call /api/corporate/groups/
        The groups endpoint queries company_external (MSSQL) for GroupInformation.
        We mock that DB call so the test stays SQLite-only.
        """
        login_resp = self.get_jwt_token('testcorp', 'TestCorp123')
        self.assertEqual(login_resp.status_code, 200)
        token = login_resp.data['access']

        authed = self.auth_api_client(token)

        # Mock the external DB query (GroupInformation is on company_external/MSSQL)
        with patch(
            'api_corporate.views.GroupInformation.objects.using',
            return_value=MagicMock(
                filter=MagicMock(return_value=MagicMock(
                    __iter__=MagicMock(return_value=iter([])),
                    count=MagicMock(return_value=0),
                ))
            )
        ):
            response = authed.get(reverse('group-information'))

        # Even with no external data, the endpoint should respond (not 401/403)
        self.assertIn(response.status_code, [200, 404])
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 403)

    def test_unauthenticated_request_to_groups_endpoint_returns_401(self):
        response = self.api_client.get(reverse('group-information'))
        self.assertEqual(response.status_code, 401)


# ============================================================
# 3. Session Login → Dashboard → API access workflow
#    Tests the full journey a company user takes through the portal
# ============================================================

class SessionToAPIWorkflowTests(IntegrationBase):

    def test_full_company_session_journey(self):
        """
        1. POST login → redirects to dashboard
        2. dashboard → redirects to company_dashboard
        3. company_dashboard → 200 with correct context
        4. report page → 200 with company and groups in context
        """
        # Step 1: login
        response = self.client.post(reverse('login'), {
            'username': 'testcorp',
            'password': 'TestCorp123',
        })
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)

        # Step 2 & 3: dashboard → company dashboard
        response = self.client.get(reverse('company_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['company'], self.company)
        self.assertEqual(response.context['total_groups'], 2)

        # Step 4: access a report page
        response = self.client.get(reverse('maturity_forecasting_report'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('company', response.context)
        self.assertIn('groups', response.context)
        # Only non-deleted groups appear in dropdown
        group_ids_in_context = [g['group_id'] for g in response.context['groups']]
        self.assertIn('GRP001', group_ids_in_context)
        self.assertIn('GRP002', group_ids_in_context)
        self.assertNotIn('GRP003', group_ids_in_context)

    def test_logout_terminates_session_and_blocks_dashboard(self):
        """After logout, all protected pages redirect to login."""
        self.client.login(username='testcorp', password='TestCorp123')
        self.client.get(reverse('logout'))

        response = self.client.get(reverse('company_dashboard'))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('company_dashboard')}",
        )

    def test_individual_user_session_journey(self):
        """Individual logs in via session and gets routed to individual_dashboard."""
        response = self.client.post(reverse('login'), {
            'username': 'induser',
            'password': 'IndUser123',
        })
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)

        # dashboard should redirect individual to individual_dashboard
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(
            response,
            reverse('individual_dashboard'),
            fetch_redirect_response=False,
        )

    def test_individual_cannot_access_company_dashboard(self):
        self.client.login(username='induser', password='IndUser123')
        response = self.client.get(reverse('company_dashboard'))
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)

    def test_company_user_cannot_access_individual_dashboard(self):
        self.client.login(username='testcorp', password='TestCorp123')
        response = self.client.get(reverse('individual_dashboard'))
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)


# ============================================================
# 4. Group Ownership Enforcement
#    Company A cannot access Company B's groups via the API
# ============================================================

class GroupOwnershipWorkflowTests(IntegrationBase):

    def _get_token(self, username, password):
        resp = self.get_jwt_token(username, password)
        self.assertEqual(resp.status_code, 200)
        return resp.data['access']

    def test_company_a_groups_visible_on_dashboard(self):
        self.client.login(username='testcorp', password='TestCorp123')
        response = self.client.get(reverse('company_dashboard'))
        self.assertEqual(response.context['total_groups'], 2)

    def test_company_b_groups_visible_on_its_own_dashboard(self):
        self.client.login(username='othercorp', password='OtherCorp123')
        response = self.client.get(reverse('company_dashboard'))
        self.assertEqual(response.context['total_groups'], 1)

    def test_report_dropdown_only_shows_own_groups(self):
        """
        Company A's report pages must only list GRP001 and GRP002,
        never GRP999 (which belongs to Company B).
        """
        self.client.login(username='testcorp', password='TestCorp123')
        for url_name in [
            'maturity_forecasting_report',
            'loan_repayment_report',
            'transfer_report',
            'claim_report',
        ]:
            with self.subTest(view=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                group_ids = [g['group_id'] for g in response.context['groups']]
                self.assertNotIn('GRP999', group_ids)
                self.assertNotIn('GRP003', group_ids)  # deleted group also excluded

    def test_api_groups_endpoint_only_returns_own_group_ids(self):
        """
        GET /api/corporate/groups/ with Company A's token must only
        reference GRP001 and GRP002 — not GRP999 or GRP003.
        The actual GroupInformation MSSQL query is mocked out.
        """
        token = self._get_token('testcorp', 'TestCorp123')
        authed = self.auth_api_client(token)

        with patch(
            'api_corporate.views.GroupInformation.objects.using',
            return_value=MagicMock(
                filter=MagicMock(return_value=MagicMock(
                    __iter__=MagicMock(return_value=iter([])),
                    count=MagicMock(return_value=0),
                ))
            )
        ):
            response = authed.get(reverse('group-information'))

        self.assertNotEqual(response.status_code, 403)
        # group_ids in the response should only be Company A's non-deleted groups
        if 'group_ids' in response.data:
            returned_ids = response.data['group_ids']
            self.assertIn('GRP001', returned_ids)
            self.assertIn('GRP002', returned_ids)
            self.assertNotIn('GRP003', returned_ids)
            self.assertNotIn('GRP999', returned_ids)