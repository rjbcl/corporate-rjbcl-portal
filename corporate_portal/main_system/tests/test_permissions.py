"""
main_system/tests/test_permissions.py
======================================
Tests for custom permission logic in main_system.

Covers:
  - @company_required decorator
  - @individual_required decorator
  - @login_required behaviour (unauthenticated redirects)
  - get_user_type() classification logic
  - Django built-in group/permission checks via has_perm()
  - View-level inline guards (company-only report/dashboard views)

Run with:
    python manage.py test main_system.tests.test_permissions \
        --settings=corporate_portal.test_settings
"""

from django.test import TestCase, RequestFactory  # type: ignore
from django.contrib.auth.models import Group as DjangoGroup, Permission  # type: ignore
from django.contrib.messages.storage.fallback import FallbackStorage  # type: ignore
from django.contrib.sessions.backends.db import SessionStore  # type: ignore
from django.http import HttpResponse  # type: ignore
from django.urls import reverse  # type: ignore
from unittest.mock import patch

from main_system.models import Account, Company, Group, Individual
from main_system.decorators import company_required, individual_required


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _add_messages(request):
    """Attach a working message storage to a bare RequestFactory request."""
    setattr(request, 'session', SessionStore())
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    return request


def _make_view(return_value="OK"):
    """Return a trivial view function whose call is detectable."""
    def inner_view(request, *args, **kwargs):
        return return_value
    return inner_view


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / shared setUp
# ─────────────────────────────────────────────────────────────────────────────

class BasePermissionTestCase(TestCase):
    """
    Creates a minimal object graph used by most tests:

        staff_user       – is_staff=True
        company_account  – linked to Company via company_profile
        company          – Company instance
        group            – Group instance owned by company
        individual_account – linked to Individual via individual_profile
        individual       – Individual instance inside group
        plain_account    – authenticated but has no profile (edge case)
    """

    @classmethod
    def setUpTestData(cls):
        # Staff user
        cls.staff_user = Account.objects.create_user(
            username='staff01', password='pass', is_staff=True
        )

        # Company account + profile
        cls.company_account = Account.objects.create_user(
            username='company01', password='pass'
        )
        cls.company = Company.objects.create(
            username=cls.company_account,
            company_name='Test Corp',
            isactive=True,
        )

        # Group owned by company
        cls.group = Group.objects.create(
            company_id=cls.company,
            group_id='GRP001',
            group_name='Alpha Group',
            isactive=True,
            isdeleted=False,
        )

        # Individual account + profile
        cls.individual_account = Account.objects.create_user(
            username='individual01', password='pass'
        )
        cls.individual = Individual.objects.create(
            username=cls.individual_account,
            group_id=cls.group,
            user_full_name='Test Person',
        )

        # Plain account (no profile attached)
        cls.plain_account = Account.objects.create_user(
            username='plain01', password='pass'
        )

        # Superuser
        cls.superuser = Account.objects.create_superuser(
            username='admin01', password='pass'
        )


# ─────────────────────────────────────────────────────────────────────────────
# 1. get_user_type()
# ─────────────────────────────────────────────────────────────────────────────

class GetUserTypeTests(BasePermissionTestCase):

    def test_superuser_returns_admin(self):
        self.assertEqual(self.superuser.get_user_type(), 'admin')

    def test_staff_returns_staff(self):
        self.assertEqual(self.staff_user.get_user_type(), 'staff')

    def test_company_account_returns_company(self):
        self.assertEqual(self.company_account.get_user_type(), 'company')

    def test_individual_account_returns_individual(self):
        self.assertEqual(self.individual_account.get_user_type(), 'individual')

    def test_plain_account_returns_none(self):
        self.assertIsNone(self.plain_account.get_user_type())

    def test_staff_flag_takes_priority_over_no_profile(self):
        """is_staff should resolve to 'staff' even without a company/individual profile."""
        self.assertEqual(self.staff_user.get_user_type(), 'staff')

    def test_superuser_takes_priority_over_staff(self):
        """is_superuser check comes before is_staff in get_user_type()."""
        both = Account.objects.create_user(
            username='both_flags', password='pass',
            is_staff=True, is_superuser=True
        )
        self.assertEqual(both.get_user_type(), 'admin')


# ─────────────────────────────────────────────────────────────────────────────
# 2. @company_required decorator
# ─────────────────────────────────────────────────────────────────────────────

class CompanyRequiredDecoratorTests(BasePermissionTestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.decorated_view = company_required(_make_view())

    def _get_request(self, user):
        request = self.factory.get('/fake-url/')
        request.user = user
        _add_messages(request)
        return request

    def test_company_user_passes_through(self):
        request = self._get_request(self.company_account)
        response = self.decorated_view(request)
        self.assertEqual(response, "OK")

    def test_unauthenticated_user_redirects_to_login(self):
        from django.contrib.auth.models import AnonymousUser
        request = self._get_request(AnonymousUser())
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])

    def test_individual_user_is_denied(self):
        request = self._get_request(self.individual_account)
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('dashboard', response['Location'])

    def test_staff_user_is_denied(self):
        request = self._get_request(self.staff_user)
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('dashboard', response['Location'])

    def test_plain_account_is_denied(self):
        request = self._get_request(self.plain_account)
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('dashboard', response['Location'])

    def test_denied_user_receives_error_message(self):
        request = self._get_request(self.individual_account)
        self.decorated_view(request)
        msgs = list(request._messages)
        self.assertTrue(any('Access denied' in str(m) for m in msgs))


# ─────────────────────────────────────────────────────────────────────────────
# 3. @individual_required decorator
# ─────────────────────────────────────────────────────────────────────────────

class IndividualRequiredDecoratorTests(BasePermissionTestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.decorated_view = individual_required(_make_view())

    def _get_request(self, user):
        request = self.factory.get('/fake-url/')
        request.user = user
        _add_messages(request)
        return request

    def test_individual_user_passes_through(self):
        request = self._get_request(self.individual_account)
        response = self.decorated_view(request)
        self.assertEqual(response, "OK")

    def test_unauthenticated_user_redirects_to_login(self):
        from django.contrib.auth.models import AnonymousUser
        request = self._get_request(AnonymousUser())
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])

    def test_company_user_is_denied(self):
        request = self._get_request(self.company_account)
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('dashboard', response['Location'])

    def test_staff_user_is_denied(self):
        request = self._get_request(self.staff_user)
        response = self.decorated_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('dashboard', response['Location'])

    def test_denied_user_receives_error_message(self):
        request = self._get_request(self.company_account)
        self.decorated_view(request)
        msgs = list(request._messages)
        self.assertTrue(any('Access denied' in str(m) for m in msgs))


# ─────────────────────────────────────────────────────────────────────────────
# 4. Django built-in group / permission system
# ─────────────────────────────────────────────────────────────────────────────

class DjangoGroupPermissionTests(BasePermissionTestCase):

    def setUp(self):
        # Create a Django group with a real model permission
        self.perm_group = DjangoGroup.objects.create(name='ReportViewers')
        perm = Permission.objects.get(codename='view_own_account')
        self.perm_group.permissions.add(perm)

    def test_user_in_group_has_permission(self):
        self.company_account.groups.add(self.perm_group)
        # Reload from DB so permission cache is fresh
        user = Account.objects.get(pk=self.company_account.pk)
        self.assertTrue(user.has_perm('main_system.view_own_account'))

    def test_user_not_in_group_lacks_permission(self):
        user = Account.objects.get(pk=self.individual_account.pk)
        self.assertFalse(user.has_perm('main_system.view_own_account'))

    def test_superuser_has_all_permissions(self):
        self.assertTrue(self.superuser.has_perm('main_system.view_own_account'))
        self.assertTrue(self.superuser.has_perm('main_system.reset_staff_password'))
        self.assertTrue(self.superuser.has_perm('main_system.soft_delete_company'))

    def test_staff_without_explicit_perm_lacks_permission(self):
        """is_staff alone does NOT grant permissions; only superuser does."""
        user = Account.objects.get(pk=self.staff_user.pk)
        self.assertFalse(user.has_perm('main_system.reset_staff_password'))

    def test_adding_direct_permission_to_user(self):
        perm = Permission.objects.get(codename='reset_staff_password')
        self.staff_user.user_permissions.add(perm)
        # Must re-fetch to clear Django's internal perm cache
        user = Account.objects.get(pk=self.staff_user.pk)
        self.assertTrue(user.has_perm('main_system.reset_staff_password'))

    def test_revoking_group_removes_permission(self):
        self.company_account.groups.add(self.perm_group)
        self.company_account.groups.remove(self.perm_group)
        user = Account.objects.get(pk=self.company_account.pk)
        self.assertFalse(user.has_perm('main_system.view_own_account'))

    def test_inactive_user_has_no_permissions(self):
        perm = Permission.objects.get(codename='view_own_account')
        self.company_account.user_permissions.add(perm)
        self.company_account.is_active = False
        self.company_account.save()
        user = Account.objects.get(pk=self.company_account.pk)
        self.assertFalse(user.has_perm('main_system.view_own_account'))

    def test_has_module_perms_for_superuser(self):
        self.assertTrue(self.superuser.has_module_perms('main_system'))

    def test_has_module_perms_for_plain_user(self):
        user = Account.objects.get(pk=self.plain_account.pk)
        self.assertFalse(user.has_module_perms('main_system'))


# ─────────────────────────────────────────────────────────────────────────────
# 5. View-level inline guards (via test client)
#    These views do their own `if get_user_type() != 'company'` guard.
# ─────────────────────────────────────────────────────────────────────────────

class CompanyOnlyViewTests(BasePermissionTestCase):
    """
    Tests the inline guard pattern used in report views:

        if request.user.get_user_type() != 'company':
            messages.error(...)
            return redirect('dashboard')

    We patch render() to avoid needing real templates.
    """

    COMPANY_ONLY_URLS = [
        '/company/groups/',
        '/company/reports/maturity-forecasting/',
        '/company/reports/transfer/',
        '/company/reports/claim/',
        '/company/reports/business-detail/',
        '/company/reports/loan-repayment/',
        '/company/reports/premium/',
        '/company/policy-summary/',
        '/company/surrender-calculator/',
    ]

    def setUp(self):
        self.client.force_login(self.company_account)

    def _login_as(self, user):
        self.client.logout()
        self.client.force_login(user)

    # ── Unauthenticated ───────────────────────────────────────────────────────

    def test_unauthenticated_redirected_to_login(self):
        self.client.logout()
        # Use company_dashboard as a representative protected view
        response = self.client.get('/company/dashboard/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'].lower())

    # ── company_dashboard (uses @company_required decorator) ──────────────────

    @patch('main_system.views.render', return_value=HttpResponse('ok'))
    def test_company_dashboard_accessible_to_company(self, mock_render):
        self.client.get('/company/dashboard/')
        # render() was called — view didn't redirect away
        self.assertTrue(mock_render.called)

    def test_company_dashboard_denied_to_individual(self):
        self._login_as(self.individual_account)
        # Do NOT follow=True — following the chain eventually hits
        # individual_dashboard which needs a real template.
        # A 302 away from this URL is sufficient proof of denial.
        response = self.client.get('/company/dashboard/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('dashboard', response['Location'])

    def test_company_dashboard_denied_to_staff(self):
        self._login_as(self.staff_user)
        response = self.client.get('/company/dashboard/', follow=False)
        self.assertEqual(response.status_code, 302)

    # ── individual_dashboard (inline guard) ───────────────────────────────────

    @patch('main_system.views.render', return_value=HttpResponse('ok'))
    def test_individual_dashboard_accessible_to_individual(self, mock_render):
        self._login_as(self.individual_account)
        self.client.get('/individual/dashboard/')
        self.assertTrue(mock_render.called)

    def test_individual_dashboard_denied_to_company(self):
        response = self.client.get('/individual/dashboard/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('dashboard', response['Location'])


# ─────────────────────────────────────────────────────────────────────────────
# 6. Login view – role-based access control at authentication time
# ─────────────────────────────────────────────────────────────────────────────

class LoginViewPermissionTests(BasePermissionTestCase):

    LOGIN_URL = '/login/'

    def test_inactive_account_cannot_login(self):
        self.company_account.is_active = False
        self.company_account.save()
        response = self.client.post(self.LOGIN_URL, {
            'username': 'company01',
            'password': 'pass',
        })
        # Should stay on the login page, not redirect to dashboard
        self.assertEqual(response.status_code, 200)

    def test_inactive_company_profile_cannot_login(self):
        self.company.isactive = False
        self.company.save()
        # Re-activate the account itself so only the profile is inactive
        self.company_account.is_active = True
        self.company_account.save()
        response = self.client.post(self.LOGIN_URL, {
            'username': 'company01',
            'password': 'pass',
        })
        self.assertEqual(response.status_code, 200)

    def test_individual_in_deleted_group_cannot_login(self):
        self.group.isdeleted = True
        self.group.save()
        response = self.client.post(self.LOGIN_URL, {
            'username': 'individual01',
            'password': 'pass',
        })
        self.assertEqual(response.status_code, 200)
        self.group.isdeleted = False  # teardown
        self.group.save()

    def test_individual_in_inactive_group_cannot_login(self):
        self.group.isactive = False
        self.group.save()
        response = self.client.post(self.LOGIN_URL, {
            'username': 'individual01',
            'password': 'pass',
        })
        self.assertEqual(response.status_code, 200)
        self.group.isactive = True
        self.group.save()

    def test_individual_with_inactive_company_cannot_login(self):
        self.company.isactive = False
        self.company.save()
        response = self.client.post(self.LOGIN_URL, {
            'username': 'individual01',
            'password': 'pass',
        })
        self.assertEqual(response.status_code, 200)
        self.company.isactive = True
        self.company.save()

    def test_valid_company_login_redirects_to_dashboard(self):
        response = self.client.post(self.LOGIN_URL, {
            'username': 'company01',
            'password': 'pass',
        }, follow=False)
        self.assertEqual(response.status_code, 302)

    def test_wrong_password_stays_on_login(self):
        response = self.client.post(self.LOGIN_URL, {
            'username': 'company01',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)

    def test_already_authenticated_user_redirected_away_from_login(self):
        self.client.force_login(self.company_account)
        response = self.client.get(self.LOGIN_URL)
        self.assertEqual(response.status_code, 302)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Dashboard routing by role
# ─────────────────────────────────────────────────────────────────────────────

class DashboardRoutingTests(BasePermissionTestCase):

    def test_staff_redirected_to_admin(self):
        self.client.force_login(self.staff_user)
        response = self.client.get('/dashboard/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/', response['Location'])

    def test_superuser_redirected_to_admin(self):
        self.client.force_login(self.superuser)
        response = self.client.get('/dashboard/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/', response['Location'])

    def test_company_redirected_to_company_dashboard(self):
        self.client.force_login(self.company_account)
        response = self.client.get('/dashboard/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('company', response['Location'])

    def test_individual_redirected_to_individual_dashboard(self):
        self.client.force_login(self.individual_account)
        response = self.client.get('/dashboard/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('individual', response['Location'])

    def test_unrecognized_user_type_is_logged_out(self):
        """A plain account (no profile) should be logged out and sent to login."""
        self.client.force_login(self.plain_account)
        response = self.client.get('/dashboard/', follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])