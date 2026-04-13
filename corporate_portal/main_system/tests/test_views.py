"""
main_system/tests/test_views.py
================================
Run with:
    python manage.py test main_system.tests.test_views --settings=corporate_portal.test_settings
"""

import json
from django.test import TestCase, Client
from django.urls import reverse
from main_system.models import Account, Company, Group, AuditLog


# ============================================================
# Helpers / Mixins
# ============================================================

class BaseTestCase(TestCase):
    """
    Creates the three user types used across all test classes.
    - company_user  : linked to a Company profile
    - staff_user    : is_staff=True, no company/individual profile
    - admin_user    : is_superuser=True
    """

    def setUp(self):
        self.client = Client()

        # --- Staff user ---
        self.staff_user = Account.objects.create_user(
            username='staffuser',
            password='StaffPass123',
            is_staff=True,
        )

        # --- Superuser / admin ---
        self.admin_user = Account.objects.create_superuser(
            username='adminuser',
            password='AdminPass123',
        )

        # --- Company account + profile ---
        self.company_account = Account.objects.create_user(
            username='companyuser',
            password='CompanyPass123',
        )
        self.company = Company.objects.create(
            username=self.company_account,
            company_name='Test Corp',
            isactive=True,
        )

    # -- convenience login helpers --

    def login_as_company(self):
        self.client.login(username='companyuser', password='CompanyPass123')

    def login_as_staff(self):
        self.client.login(username='staffuser', password='StaffPass123')

    def login_as_admin(self):
        self.client.login(username='adminuser', password='AdminPass123')


# ============================================================
# 1. Login View
# ============================================================

class LoginViewTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('login')

    # GET ----------------------------------------------------------------

    def test_get_login_page_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_authenticated_user_redirects_to_dashboard(self):
        self.login_as_company()
        response = self.client.get(self.url)
        # dashboard itself redirects further, so don't follow the chain
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)

    # POST - failure cases -----------------------------------------------

    def test_post_wrong_credentials_stays_on_login(self):
        response = self.client.post(self.url, {
            'username': 'companyuser',
            'password': 'WrongPassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        messages = list(response.context['messages'])
        self.assertTrue(any('Invalid' in str(m) for m in messages))

    def test_post_inactive_account_blocked(self):
        self.company_account.is_active = False
        self.company_account.save()

        response = self.client.post(self.url, {
            'username': 'companyuser',
            'password': 'CompanyPass123',
        })
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        # Django's ModelBackend rejects inactive users before the view runs,
        # so authenticate() returns None → the generic 'Invalid' message fires.
        self.assertTrue(any('Invalid' in str(m) for m in messages))

    def test_post_inactive_company_profile_blocked(self):
        self.company.isactive = False
        self.company.save()

        response = self.client.post(self.url, {
            'username': 'companyuser',
            'password': 'CompanyPass123',
        })
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('inactive' in str(m).lower() for m in messages))

    # POST - success -----------------------------------------------------

    def test_post_valid_company_login_redirects_to_dashboard(self):
        response = self.client.post(self.url, {
            'username': 'companyuser',
            'password': 'CompanyPass123',
        })
        # dashboard redirects onward; don't follow the chain
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)

    def test_post_valid_staff_login_redirects_to_dashboard(self):
        response = self.client.post(self.url, {
            'username': 'staffuser',
            'password': 'StaffPass123',
        })
        # dashboard redirects onward; don't follow the chain
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)


# ============================================================
# 2. Dashboard Routing
# ============================================================

class DashboardRoutingTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('dashboard')

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_company_user_redirected_to_company_dashboard(self):
        self.login_as_company()
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('company_dashboard'), fetch_redirect_response=False)

    def test_staff_user_redirected_to_admin(self):
        self.login_as_staff()
        response = self.client.get(self.url)
        self.assertRedirects(response, '/admin/', fetch_redirect_response=False)

    def test_admin_user_redirected_to_admin(self):
        self.login_as_admin()
        response = self.client.get(self.url)
        self.assertRedirects(response, '/admin/', fetch_redirect_response=False)


# ============================================================
# 3. Company Dashboard
# ============================================================

class CompanyDashboardTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('company_dashboard')

        # Create a group so total_groups count is testable
        Group.objects.create(
            company_id=self.company,
            group_id='GRP001',
            group_name='Test Group',
            isdeleted=False,
            isactive=True,
        )

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_company_user_gets_200(self):
        self.login_as_company()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Dashboard/Company/dashboard.html')

    def test_company_context_contains_company_and_groups(self):
        self.login_as_company()
        response = self.client.get(self.url)
        self.assertIn('company', response.context)
        self.assertIn('total_groups', response.context)
        self.assertEqual(response.context['total_groups'], 1)

    def test_staff_user_redirected_by_decorator(self):
        self.login_as_staff()
        response = self.client.get(self.url)
        # decorator redirects to dashboard which itself redirects; don't follow
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)

    def test_deleted_group_not_counted(self):
        Group.objects.create(
            company_id=self.company,
            group_id='GRP002',
            group_name='Deleted Group',
            isdeleted=True,
        )
        self.login_as_company()
        response = self.client.get(self.url)
        # Only the non-deleted group from setUp should be counted
        self.assertEqual(response.context['total_groups'], 1)


# ============================================================
# 4. Company Groups View
# ============================================================

class CompanyGroupsViewTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('company_groups')

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_company_user_gets_200(self):
        self.login_as_company()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Dashboard/Company/groups.html')

    def test_staff_user_denied_and_redirected_to_dashboard(self):
        self.login_as_staff()
        response = self.client.get(self.url)
        # dashboard itself redirects; don't follow the chain
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('Access denied' in str(m) for m in messages))


# ============================================================
# 5. Company Report Views (parametrized via loop)
# ============================================================

COMPANY_REPORT_URLS = [
    ('maturity_forecasting_report', 'Dashboard/Company/reports/maturity_forecasting_report.html'),
    ('loan_repayment_report',       'Dashboard/Company/reports/group_loan_report.html'),
    ('transfer_report',             'Dashboard/Company/reports/Transfer_report.html'),
    ('claim_report',                'Dashboard/Company/reports/claim_report.html'),
    ('policy_summary',              'Dashboard/Company/policy_summary_report.html'),
    ('surrender_calculator',        'Dashboard/Company/surrender_calculator.html'),
    ('business_detail_report',      'Dashboard/Company/reports/Business_detail_report.html'),
]


class CompanyReportViewTests(BaseTestCase):
    """
    Runs the same three assertions for every company report view:
        1. Unauthenticated → redirect to login
        2. Company user    → 200 + correct template
        3. Staff user      → redirect to dashboard + "Access denied" message
    """

    def setUp(self):
        super().setUp()
        # Provide at least one group so dropdowns aren't empty
        Group.objects.create(
            company_id=self.company,
            group_id='GRP001',
            group_name='Test Group',
            isdeleted=False,
            isactive=True,
        )

    def _assert_report_view(self, url_name, template):
        url = reverse(url_name)

        # 1. Unauthenticated
        self.client.logout()
        response = self.client.get(url)
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={url}",
            msg_prefix=f"[{url_name}] unauthenticated should redirect to login",
        )

        # 2. Company user
        self.login_as_company()
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, 200,
            msg=f"[{url_name}] company user should get 200",
        )
        self.assertTemplateUsed(response, template)
        # Context must include company and groups
        self.assertIn('company', response.context)
        if 'groups' in response.context:
            # Views that pass a groups queryset: confirm it's non-empty
            self.assertGreaterEqual(len(response.context['groups']), 1)
        self.client.logout()

        # 3. Staff user (non-company) denied
        self.login_as_staff()
        response = self.client.get(url)
        # dashboard itself redirects onward; don't follow the chain
        self.assertRedirects(
            response,
            reverse('dashboard'),
            fetch_redirect_response=False,
            msg_prefix=f"[{url_name}] staff user should be redirected to dashboard",
        )
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any('Access denied' in str(m) for m in messages),
            msg=f"[{url_name}] should show 'Access denied' message",
        )
        self.client.logout()

    def test_all_report_views(self):
        for url_name, template in COMPANY_REPORT_URLS:
            with self.subTest(view=url_name):
                self._assert_report_view(url_name, template)


# ============================================================
# 6. Change Password View
# ============================================================

class ChangePasswordViewTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('change_password')

    def _post(self, data):
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json',
        )

    # Access control -----------------------------------------------------

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.post(self.url, {})
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_get_request_returns_405(self):
        self.login_as_company()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    # Validation failures ------------------------------------------------

    def test_wrong_current_password_returns_400(self):
        self.login_as_company()
        response = self.client.post(self.url, {
            'current_password': 'WrongPassword',
            'new_password':     'NewPassword123',
            'confirm_password': 'NewPassword123',
        })
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body['success'])
        self.assertIn('current_password', body['errors'])

    def test_passwords_do_not_match_returns_400(self):
        self.login_as_company()
        response = self.client.post(self.url, {
            'current_password': 'CompanyPass123',
            'new_password':     'NewPassword123',
            'confirm_password': 'DifferentPassword123',
        })
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body['success'])

    def test_new_password_too_short_returns_400(self):
        self.login_as_company()
        response = self.client.post(self.url, {
            'current_password': 'CompanyPass123',
            'new_password':     'short',
            'confirm_password': 'short',
        })
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body['success'])

    # Success path -------------------------------------------------------

    def test_valid_change_password_returns_200(self):
        self.login_as_company()
        response = self.client.post(self.url, {
            'current_password': 'CompanyPass123',
            'new_password':     'NewStrongPass123',
            'confirm_password': 'NewStrongPass123',
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['success'])

    def test_user_remains_logged_in_after_password_change(self):
        self.login_as_company()
        self.client.post(self.url, {
            'current_password': 'CompanyPass123',
            'new_password':     'NewStrongPass123',
            'confirm_password': 'NewStrongPass123',
        })
        # dashboard always redirects (302) based on user type — that's expected.
        # What we verify is that the redirect is NOT back to login (session still valid).
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(reverse('login'), response['Location'])

    def test_audit_log_created_on_password_change(self):
        self.login_as_company()
        before_count = AuditLog.objects.count()
        self.client.post(self.url, {
            'current_password': 'CompanyPass123',
            'new_password':     'NewStrongPass123',
            'confirm_password': 'NewStrongPass123',
        })
        self.assertEqual(AuditLog.objects.count(), before_count + 1)
        log = AuditLog.objects.latest('timestamp')
        self.assertEqual(log.action, 'password_reset')
        self.assertEqual(log.performed_by, 'companyuser')


# ============================================================
# 7. Logout View
# ============================================================

class LogoutViewTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('logout')

    def test_logout_redirects_to_login(self):
        self.login_as_company()
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('login'))

    def test_session_cleared_after_logout(self):
        self.login_as_company()
        self.client.get(self.url)
        # After logout, dashboard should redirect to login
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")