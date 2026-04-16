"""
api_corporate/tests/test_api_auth.py
=====================================
JWT authentication test suite — unittest style (manage.py compatible).

Run with:
    python manage.py test api_corporate.tests.test_api_auth \
        --settings=corporate_portal.test_settings -v 2

Key behaviour confirmed from CustomTokenObtainPairView:
  - Only active company accounts (company_profile.isactive=True) receive tokens
  - Non-company users (plain / staff) → 403 {"error": "Only company accounts can access the API"}
  - Inactive company profile (isactive=False)  → 403
  - Missing fields / bad credentials → 401 (custom view handles before DRF validation)
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.authentication import JWTAuthentication

from main_system.models import Account, Company


# ===========================================================================
# Shared base
# ===========================================================================

class JWTTestBase(TestCase):
    """
    All URLs are resolved inside setUp() — never at module level — to avoid
    import-time AppRegistryNotReady / NoReverseMatch crashes.

    Account matrix:
        company_user      → active Account + active Company   → tokens issued  ✓
        dead_company_user → active Account + inactive Company → 403            ✗
        plain_user        → active Account, no company profile → 403           ✗
        inactive_user     → Account.is_active=False           → 401            ✗
    """

    def setUp(self):
        self.TOKEN_OBTAIN_URL  = reverse("token_obtain_pair")   # /api/corporate/auth/login/
        self.TOKEN_REFRESH_URL = reverse("token_refresh")       # /api/corporate/auth/refresh/
        self.client = APIClient()

        # ── Active company user (the ONLY user type that can get tokens) ──
        self.company_user = Account.objects.create_user(
            username="test_company",
            password="StrongPass!1",
        )
        Company.objects.create(
            username=self.company_user,
            company_name="Test Corp",
            isactive=True,
        )

        # ── Inactive company profile ──
        self.dead_company_user = Account.objects.create_user(
            username="dead_company",
            password="StrongPass!1",
        )
        Company.objects.create(
            username=self.dead_company_user,
            company_name="Dead Corp",
            isactive=False,
        )

        # ── No company profile at all ──
        self.plain_user = Account.objects.create_user(
            username="test_plain",
            password="StrongPass!1",
        )

        # ── Account-level inactive ──
        self.inactive_user = Account.objects.create_user(
            username="inactive_user",
            password="StrongPass!1",
            is_active=False,
        )

    def obtain_tokens(self, username, password):
        """POST to the obtain-pair endpoint, return the full response."""
        return self.client.post(
            self.TOKEN_OBTAIN_URL,
            {"username": username, "password": password},
            format="json",
        )

    def get_company_tokens(self):
        """Convenience: obtain valid tokens for the active company user."""
        return self.obtain_tokens("test_company", "StrongPass!1").data


# ===========================================================================
# 1. Token Generation — Happy Path
# ===========================================================================

class TestTokenGenerationSuccess(JWTTestBase):
    """
    Only active company accounts should receive tokens.
    All tests in this class use company_user (the only valid caller).
    """

    def test_active_company_returns_200(self):
        response = self.obtain_tokens("test_company", "StrongPass!1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_contains_access_token(self):
        response = self.obtain_tokens("test_company", "StrongPass!1")
        self.assertIn("access", response.data)

    def test_response_contains_refresh_token(self):
        response = self.obtain_tokens("test_company", "StrongPass!1")
        self.assertIn("refresh", response.data)

    def test_access_token_carries_user_id_claim(self):
        """
        Per settings.py  USER_ID_FIELD='username'  USER_ID_CLAIM='user_id'
        → token['user_id'] must equal the username string, not a numeric PK.
        """
        response = self.obtain_tokens("test_company", "StrongPass!1")
        token = AccessToken(response.data["access"])
        self.assertEqual(token["user_id"], self.company_user.username)

    def test_access_token_type_claim_is_access(self):
        response = self.obtain_tokens("test_company", "StrongPass!1")
        token = AccessToken(response.data["access"])
        self.assertEqual(token["token_type"], "access")

    def test_access_token_algorithm_is_hs256(self):
        """Token header must declare HS256 as configured in settings.py."""
        import base64, json
        response = self.obtain_tokens("test_company", "StrongPass!1")
        access_str = response.data["access"]
        header_b64 = access_str.split(".")[0]
        padded = header_b64 + "=" * (4 - len(header_b64) % 4)
        header = json.loads(base64.urlsafe_b64decode(padded))
        self.assertEqual(header["alg"], "HS256")


# ===========================================================================
# 2. Token Generation — Rejection Cases
# ===========================================================================

class TestTokenGenerationRejection(JWTTestBase):
    """
    CustomTokenObtainPairView enforces company-only access.
    Every non-company path must be blocked before a token is issued.
    """

    def test_wrong_password_returns_401(self):
        response = self.obtain_tokens("test_company", "WrongPassword!")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_user_returns_401(self):
        response = self.obtain_tokens("ghost_user", "AnyPass!1")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_plain_user_no_company_profile_is_rejected(self):
        """Non-company account → custom view returns 403."""
        response = self.obtain_tokens("test_plain", "StrongPass!1")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_plain_user_rejection_contains_error_message(self):
        response = self.obtain_tokens("test_plain", "StrongPass!1")
        self.assertIn("error", response.data)

    def test_inactive_account_is_rejected(self):
        """Account.is_active=False → simplejwt rejects before company check."""
        response = self.obtain_tokens("inactive_user", "StrongPass!1")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_company_profile_is_rejected(self):
        """
        company.isactive=False → custom view blocks and returns 403.
        The JWT must NOT be issued even though Account.is_active=True.
        """
        response = self.obtain_tokens("dead_company", "StrongPass!1")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_company_rejection_contains_error_message(self):
        response = self.obtain_tokens("dead_company", "StrongPass!1")
        self.assertIn("error", response.data)

    def test_missing_username_is_rejected(self):
        """Custom view returns 401 for missing credentials (not standard 400)."""
        response = self.client.post(
            self.TOKEN_OBTAIN_URL, {"password": "StrongPass!1"}, format="json"
        )
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ])

    def test_missing_password_is_rejected(self):
        response = self.client.post(
            self.TOKEN_OBTAIN_URL, {"username": "test_company"}, format="json"
        )
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ])

    def test_empty_body_is_rejected(self):
        response = self.client.post(self.TOKEN_OBTAIN_URL, {}, format="json")
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ])


# ===========================================================================
# 3. Token Refresh
# ===========================================================================

class TestTokenRefresh(JWTTestBase):
    """POST /api/corporate/auth/refresh/ — exchange refresh for new access token."""

    def test_valid_refresh_token_returns_200(self):
        tokens = self.get_company_tokens()
        response = self.client.post(
            self.TOKEN_REFRESH_URL, {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_refresh_response_contains_access_token(self):
        tokens = self.get_company_tokens()
        response = self.client.post(
            self.TOKEN_REFRESH_URL, {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertIn("access", response.data)

    def test_new_access_token_has_correct_user_id(self):
        """The refreshed token must still carry the same user_id claim."""
        tokens = self.get_company_tokens()
        refresh_response = self.client.post(
            self.TOKEN_REFRESH_URL, {"refresh": tokens["refresh"]}, format="json"
        )
        new_token = AccessToken(refresh_response.data["access"])
        self.assertEqual(new_token["user_id"], self.company_user.username)

    def test_invalid_refresh_token_returns_401(self):
        response = self.client.post(
            self.TOKEN_REFRESH_URL, {"refresh": "this.is.garbage"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_refresh_field_returns_400(self):
        response = self.client.post(self.TOKEN_REFRESH_URL, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_access_token_cannot_be_used_as_refresh(self):
        """Passing an access token to the refresh endpoint must be rejected."""
        tokens = self.get_company_tokens()
        response = self.client.post(
            self.TOKEN_REFRESH_URL,
            {"refresh": tokens["access"]},   # deliberately wrong token type
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rotate_refresh_tokens_is_off(self):
        """
        ROTATE_REFRESH_TOKENS = False in settings.py.
        The refresh response must NOT contain a new refresh token.
        """
        tokens = self.get_company_tokens()
        response = self.client.post(
            self.TOKEN_REFRESH_URL, {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertNotIn("refresh", response.data)


# ===========================================================================
# 4. Token Validation
# ===========================================================================

class TestTokenValidation(JWTTestBase):
    """Structural integrity — decode, tamper detection, Bearer resolution."""

    def test_valid_access_token_decodes_without_error(self):
        """AccessToken() raises TokenError on any decode failure."""
        tokens = self.get_company_tokens()
        token = AccessToken(tokens["access"])
        self.assertEqual(token["user_id"], self.company_user.username)

    def test_tampered_signature_raises_token_error(self):
        """Flipping one character in the signature must raise TokenError."""
        refresh = RefreshToken.for_user(self.company_user)
        access_str = str(refresh.access_token)

        header_payload, signature = access_str.rsplit(".", 1)
        bad_char = "B" if signature[-1] != "B" else "C"
        bad_token = header_payload + "." + signature[:-1] + bad_char

        with self.assertRaises(TokenError):
            AccessToken(bad_token)

    def test_bearer_header_resolves_to_correct_user(self):
        """
        JWTAuthentication.authenticate() must resolve a Bearer token
        back to the originating company user.
        """
        tokens = self.get_company_tokens()

        factory = APIRequestFactory()
        request = factory.get("/")
        request.META["HTTP_AUTHORIZATION"] = f"Bearer {tokens['access']}"

        auth = JWTAuthentication()
        validated_user, _ = auth.authenticate(request)
        self.assertEqual(validated_user.username, self.company_user.username)

    def test_api_client_credentials_carries_bearer_header(self):
        """credentials() on the APIClient must set the Authorization header."""
        tokens = self.get_company_tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertIn("HTTP_AUTHORIZATION", self.client._credentials)


# ===========================================================================
# 5. Company Account Specifics
# ===========================================================================

class TestCompanyAccount(JWTTestBase):
    """
    Validates the company-account-specific access control enforced by
    CustomTokenObtainPairView and the model helper methods.
    """

    def test_active_company_user_type_resolves_correctly(self):
        user = Account.objects.get(username="test_company")
        self.assertEqual(user.get_user_type(), "company")

    def test_active_company_display_name_is_company_name(self):
        user = Account.objects.get(username="test_company")
        self.assertEqual(user.get_display_name(), "Test Corp")

    def test_inactive_company_user_type_still_resolves_as_company(self):
        """Profile type detection is independent of the isactive flag."""
        user = Account.objects.get(username="dead_company")
        self.assertEqual(user.get_user_type(), "company")

    def test_active_company_profile_flag_is_true(self):
        user = Account.objects.get(username="test_company")
        self.assertTrue(user.company_profile.isactive)

    def test_inactive_company_profile_flag_is_false(self):
        user = Account.objects.get(username="dead_company")
        self.assertFalse(user.company_profile.isactive)

    def test_company_token_user_id_claim_matches_username(self):
        """
        After a successful login the token's user_id claim must equal
        the username string (USER_ID_FIELD = 'username' in settings.py).
        """
        tokens = self.get_company_tokens()
        token = AccessToken(tokens["access"])
        self.assertEqual(token["user_id"], "test_company")

    def test_inactive_company_cannot_obtain_token(self):
        """Dead company account must be blocked at the login endpoint."""
        response = self.obtain_tokens("dead_company", "StrongPass!1")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_token_resolves_back_to_company_profile(self):
        """
        Decoding a valid token and looking up the user from DB must give
        access to company_profile — the downstream permission layer relies on this.
        """
        tokens = self.get_company_tokens()
        token = AccessToken(tokens["access"])
        user = Account.objects.get(username=token["user_id"])
        self.assertTrue(hasattr(user, "company_profile"))
        self.assertEqual(user.company_profile.company_name, "Test Corp")


# ===========================================================================
# 6. Token Construction (unit-level, no HTTP)
# ===========================================================================

class TestTokenConstruction(TestCase):
    """
    Directly instantiate simplejwt token objects — tests token mechanics
    independently of any HTTP view, URL config, or custom view logic.
    """

    def setUp(self):
        self.user = Account.objects.create_user(
            username="unit_user", password="Pass!99"
        )

    def test_refresh_token_for_user_contains_user_id(self):
        refresh = RefreshToken.for_user(self.user)
        self.assertEqual(refresh["user_id"], self.user.username)

    def test_access_token_derived_from_refresh_has_correct_claims(self):
        refresh = RefreshToken.for_user(self.user)
        access = refresh.access_token
        self.assertEqual(access["token_type"], "access")
        self.assertEqual(access["user_id"], self.user.username)

    def test_same_refresh_token_decodable_twice_when_rotation_off(self):
        """
        ROTATE_REFRESH_TOKENS = False — reading the same refresh string twice
        must not raise (no blacklist triggered on decode).
        """
        refresh = RefreshToken.for_user(self.user)
        token_str = str(refresh)
        t1 = RefreshToken(token_str)
        t2 = RefreshToken(token_str)
        self.assertEqual(t1["user_id"], t2["user_id"])

    def test_access_token_algorithm_is_hs256(self):
        import base64, json
        refresh = RefreshToken.for_user(self.user)
        access_str = str(refresh.access_token)
        header_b64 = access_str.split(".")[0]
        padded = header_b64 + "=" * (4 - len(header_b64) % 4)
        header = json.loads(base64.urlsafe_b64decode(padded))
        self.assertEqual(header["alg"], "HS256")