from django.utils import timezone  # type: ignore
from django.conf import settings  # type: ignore

from rest_framework.authentication import BaseAuthentication  # type: ignore
from rest_framework.exceptions import AuthenticationFailed  # type: ignore

from main_system.models import AuditLog, CompanyAccount


class APIKeyAuthentication(BaseAuthentication):
    """
    DRF authentication class for 3rd party server-to-server requests.

    Expects header:
        X-API-Key: copo_<64 hex chars>

    Validation order:
        1. Header present
        2. Key exists in DB and is_active=True
        3. Company is active
        4. Company has an approved primary account
        5. Attaches primary account as request.user

    Logs all failures and successes to AuditLog.
    Rate limiting is enforced via API_RATE_LIMIT in settings.
    """

    HEADER = 'HTTP_X_API_KEY'

    def authenticate(self, request):
        raw_key = request.META.get(self.HEADER)

        if not raw_key:
            # No API key header — let other authenticators (Session) try
            return None

        from .models import APIKey

        api_key = APIKey.lookup(raw_key)

        if api_key is None:
            AuditLog.create_log(
                action='login_failed',
                target_username='unknown',
                target_type='api_key',
                performed_by='unknown',
                details='Invalid or revoked API key.',
                ip_address=self._get_ip(request),
            )
            raise AuthenticationFailed('Invalid or revoked API key.')

        company = api_key.company

        if not company.isactive:
            AuditLog.create_log(
                action='login_failed',
                target_username=company.company_name,
                target_type='api_key',
                performed_by=company.company_name,
                details='API key rejected — company is inactive.',
                ip_address=self._get_ip(request),
            )
            raise AuthenticationFailed('Company account is inactive.')

        # Fetch approved primary account — runtime safety net
        primary_account = CompanyAccount.objects.filter(
            company=company,
            is_primary=True,
            is_approved=True,
        ).select_related('account').first()

        if primary_account is None:
            AuditLog.create_log(
                action='login_failed',
                target_username=company.company_name,
                target_type='api_key',
                performed_by=company.company_name,
                details='API key rejected — no approved primary account found.',
                ip_address=self._get_ip(request),
            )
            raise AuthenticationFailed(
                'No approved primary account found for this company.'
            )

        user = primary_account.account

        if not user.is_active:
            AuditLog.create_log(
                action='login_failed',
                target_username=user.username,
                target_type='api_key',
                performed_by=user.username,
                details='API key rejected — primary account is inactive.',
                ip_address=self._get_ip(request),
            )
            raise AuthenticationFailed('Primary account is inactive.')

        # Update last_used_at without triggering full model save overhead
        APIKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())

        AuditLog.create_log(
            action='login',
            target_username=user.username,
            target_type='api_key',
            performed_by=user.username,
            details=f"API key authenticated for company '{company.company_name}'.",
            ip_address=self._get_ip(request),
        )

        return (user, api_key)

    def authenticate_header(self, request):
        return 'X-API-Key'

    @staticmethod
    def _get_ip(request):
        return request.META.get('REMOTE_ADDR')