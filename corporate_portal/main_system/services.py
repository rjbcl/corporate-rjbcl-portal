import pyotp
import json
import hashlib
import logging

from datetime import timedelta

from django.db import transaction  # type: ignore
from django.core.exceptions import ValidationError, PermissionDenied  # type: ignore
from django.utils import timezone
from django.conf import settings

from .models import AuditLog, Company, Group, Account, CompanyAccount, UserVerification
from .utils import validate_password_strength

logger = logging.getLogger(__name__)


# ============================================================
# PERMISSION MIXIN
# ============================================================

class PermissionMixin:
    """Mixin for permission checking across all services."""

    @staticmethod
    def check_permission(user, permission_string, raise_exception=True):
        if not user:
            if raise_exception:
                raise PermissionDenied("User authentication required")
            return False

        if user.is_superuser:
            return True

        has_perm = user.has_perm(permission_string)

        if not has_perm and raise_exception:
            raise PermissionDenied(f"You don't have permission: {permission_string}")

        return has_perm


# ============================================================
# COMPANY SERVICE
# ============================================================

class CompanyService(PermissionMixin):

    @staticmethod
    def validate_group_availability(group_ids, exclude_company_id=None):
        """Validate that groups are not already assigned to other companies."""
        if not group_ids:
            return None

        existing_groups = Group.objects.filter(
            group_id__in=group_ids,
            isdeleted=False
        )

        if exclude_company_id:
            existing_groups = existing_groups.exclude(company_id=exclude_company_id)

        if existing_groups.exists():
            conflicts = []
            for group in existing_groups:
                conflicts.append({
                    'group_id': group.group_id,
                    'group_name': group.group_name,
                    'company_name': group.company.company_name,
                })
            return conflicts

        return None

    @staticmethod
    @transaction.atomic
    def create_company(company_data, group_ids, groups_lookup, user=None):
        """Create a new company with its groups."""

        CompanyService.check_permission(user, 'main_system.add_company')

        conflicts = CompanyService.validate_group_availability(group_ids)
        if conflicts:
            conflict_msgs = [
                f"{c['group_id']} ({c['group_name']}) - already assigned to {c['company_name']}"
                for c in conflicts
            ]
            raise ValidationError(
                f"The following groups are already assigned to other companies: {', '.join(conflict_msgs)}"
            )

        if user:
            company_data['created_by'] = user.username
            company_data['modified_by'] = user.username

        company = Company.objects.create(**company_data)

        for gid in group_ids:
            group_name = groups_lookup.get(gid, '')

            orphaned_group = Group.objects.filter(
                group_id=gid,
                isdeleted=True
            ).first()

            if orphaned_group:
                orphaned_group.company = company
                orphaned_group.isdeleted = False
                orphaned_group.isactive = company.isactive
                orphaned_group.group_name = group_name
                if user:
                    orphaned_group.modified_by = user.username
                orphaned_group.save()

            else:
                group_data = {
                    'company': company,
                    'group_id': gid,
                    'group_name': group_name,
                    'isactive': company.isactive,
                }
                if user:
                    group_data['created_by'] = user.username
                    group_data['modified_by'] = user.username

                Group.objects.create(**group_data)

        if user:
            AuditLog.create_log(
                action='create',
                target_username=company.company_name,
                target_type='company',
                performed_by=user.username,
                details=json.dumps({
                    'company_name': company.company_name,
                    'groups_assigned': list(group_ids),
                })
            )

        return company

    @staticmethod
    @transaction.atomic
    def update_company(company, company_data=None, group_ids=None, groups_lookup=None, user=None):
        """Update an existing company and optionally its groups."""

        CompanyService.check_permission(user, 'main_system.change_company')

        changes = {}

        if group_ids is not None:
            conflicts = CompanyService.validate_group_availability(
                group_ids, exclude_company_id=company.company_id
            )
            if conflicts:
                conflict_msgs = [
                    f"{c['group_id']} ({c['group_name']}) - already assigned to {c['company_name']}"
                    for c in conflicts
                ]
                raise ValidationError(
                    f"The following groups are already assigned to other companies: {', '.join(conflict_msgs)}"
                )

        if company_data:
            for field, new_value in company_data.items():
                if field in ['modified_by', 'created_by']:
                    continue

                old_value = getattr(company, field, None)

                if isinstance(old_value, bool) and isinstance(new_value, bool):
                    if old_value != new_value:
                        changes[field] = {'old': old_value, 'new': new_value}
                elif old_value is None and new_value is None:
                    continue
                elif old_value is None or new_value is None:
                    if old_value != new_value:
                        changes[field] = {
                            'old': str(old_value) if old_value is not None else 'None',
                            'new': str(new_value) if new_value is not None else 'None',
                        }
                elif str(old_value).strip() != str(new_value).strip():
                    changes[field] = {'old': str(old_value), 'new': str(new_value)}

            if user:
                company_data['modified_by'] = user.username

            for field, value in company_data.items():
                setattr(company, field, value)
            company.save()

        # If company goes inactive, cascade to groups and accounts
        if company_data and not company.isactive:
            Group.objects.filter(company=company).update(
                isactive=False,
                modified_by=user.username if user else None,
            )
            Account.objects.filter(
                company_profile__company=company
            ).update(
                is_active=False,
                modified_by=user.username if user else None,
            )

        if group_ids is not None and groups_lookup is not None:
            old_groups = list(
                Group.objects.filter(company=company, isdeleted=False)
                .values_list('group_id', flat=True)
            )

            Group.objects.filter(company=company).update(
                isdeleted=True,
                isactive=False,
                modified_by=user.username if user else None,
            )

            for gid in group_ids:
                group_name = groups_lookup.get(gid, '')

                existing_group = Group.objects.filter(
                    company=company,
                    group_id=gid
                ).first()

                if existing_group:
                    existing_group.isdeleted = False
                    existing_group.isactive = company.isactive
                    existing_group.group_name = group_name
                    if user:
                        existing_group.modified_by = user.username
                    existing_group.save()

                else:
                    orphaned_group = Group.objects.filter(
                        group_id=gid,
                        isdeleted=True
                    ).exclude(company=company).first()

                    if orphaned_group:
                        orphaned_group.company = company
                        orphaned_group.isdeleted = False
                        orphaned_group.isactive = company.isactive
                        orphaned_group.group_name = group_name
                        if user:
                            orphaned_group.modified_by = user.username
                        orphaned_group.save()

                    else:
                        group_data = {
                            'company': company,
                            'group_id': gid,
                            'group_name': group_name,
                            'isactive': company.isactive,
                        }
                        if user:
                            group_data['created_by'] = user.username
                            group_data['modified_by'] = user.username

                        Group.objects.create(**group_data)

            new_groups = list(group_ids)
            if set(old_groups) != set(new_groups):
                changes['groups'] = {'old': old_groups, 'new': new_groups}

        if changes and user:
            AuditLog.create_log(
                action='update',
                target_username=company.company_name,
                target_type='company',
                performed_by=user.username,
                details=json.dumps(changes),
            )

        return company

    @staticmethod
    @transaction.atomic
    def soft_delete_company(company, user=None):
        """Soft delete a company — sets isactive=False, cascades to groups and accounts."""
        CompanyService.check_permission(user, 'main_system.soft_delete_company')

        company.isactive = False
        if user:
            company.modified_by = user.username
        company.save()

        Group.objects.filter(company=company).update(
            isactive=False,
            isdeleted=True,
            modified_by=user.username if user else None,
        )

        Account.objects.filter(
            company_profile__company=company
        ).update(
            is_active=False,
            modified_by=user.username if user else None,
        )

        if user:
            AuditLog.create_log(
                action='soft_delete',
                target_username=company.company_name,
                target_type='company',
                performed_by=user.username,
                details=f"Company '{company.company_name}' soft deleted.",
            )

        return company

    @staticmethod
    @transaction.atomic
    def hard_delete_company(company, user=None):
        """Hard delete a company (admin only). Cascades to all linked accounts."""
        CompanyService.check_permission(user, 'main_system.delete_company')

        company_name = company.company_name
        company_id = company.company_id

        if user:
            AuditLog.create_log(
                action='hard_delete',
                target_username=company_name,
                target_type='company',
                performed_by=user.username,
                details=json.dumps({
                    'company_name': company_name,
                    'company_id': company_id,
                })
            )

        Account.objects.filter(company_profile__company=company).delete()
        company.delete()

        return True

    @staticmethod
    @transaction.atomic
    def approve_company(company, user=None):
        """Approve a company — reactivates company, groups, and all linked accounts."""
        CompanyService.check_permission(user, 'main_system.approve_company')

        company.isactive = True
        if user:
            company.modified_by = user.username
        company.save()

        Group.objects.filter(company=company).update(
            isactive=True,
            isdeleted=False,
            modified_by=user.username if user else None,
        )

        Account.objects.filter(
            company_profile__company=company
        ).update(
            is_active=True,
            modified_by=user.username if user else None,
        )

        if user:
            AuditLog.create_log(
                action='update',
                target_username=company.company_name,
                target_type='company',
                performed_by=user.username,
                details=f"Company '{company.company_name}' approved and activated.",
            )

        return company

    @staticmethod
    @transaction.atomic
    def update_company_info(company, info_data, user=None):
        """
        Updates the primary contact fields on Company.
        Called from the portal by the primary company account user.
        Fields: primary_contact_person, primary_person_mobile,
                primary_person_email, pan_number.
        """
        allowed_fields = {
            'primary_contact_person',
            'primary_person_mobile',
            'primary_person_email',
            'pan_number',
            'nepali_name',
            'email',
            'phone_number',
            'telephone_number',
        }

        changes = {}
        for field, new_value in info_data.items():
            if field not in allowed_fields:
                continue
            old_value = getattr(company, field, None)

            # Skip if field already has data — primary user can only fill empty fields
            if old_value is not None and str(old_value).strip() != '':
                continue

            # Skip if new value is also empty — nothing to do
            if new_value is None or str(new_value).strip() == '':
                continue

            changes[field] = {'old': str(old_value), 'new': str(new_value)}
            setattr(company, field, new_value)

        if user:
            company.modified_by = user.username
        company.save()

        if changes and user:
            AuditLog.create_log(
                action='update',
                target_username=company.company_name,
                target_type='company',
                performed_by=user.username,
                details=json.dumps(changes),
            )

        return company


# ============================================================
# COMPANY ACCOUNT SERVICE
# ============================================================

class CompanyAccountService(PermissionMixin):
    """
    Handles all operations on company staff accounts.
    Every operation manages Account + CompanyAccount + UserVerification
    atomically — no orphaned rows are ever possible.

    Two creation paths:
      Admin path  (enforce_limit=False): staff creates via Django admin,
                  is_approved=True, no account limit enforced.
      Portal path (enforce_limit=True):  primary user creates via portal,
                  is_approved=False, account limit enforced.
    """

    MAX_ACCOUNTS_PER_COMPANY = 5

    @staticmethod
    def _validate_password(password):
        """Validates password strength if ENFORCE_PASSWORD_STRENGTH is True."""
        if not getattr(settings, 'ENFORCE_PASSWORD_STRENGTH', False):
            return
        errors = validate_password_strength(password)
        if errors:
            raise ValidationError(f"Password must contain: {', '.join(errors)}.")

    @staticmethod
    def _enforce_single_primary(company, exclude_account=None):
        """Ensures only one CompanyAccount per company has is_primary=True."""
        qs = CompanyAccount.objects.filter(company=company, is_primary=True)
        if exclude_account:
            qs = qs.exclude(account=exclude_account)
        qs.update(is_primary=False)

    @staticmethod
    def _check_account_limit(company):
        """
        Enforces MAX_ACCOUNTS_PER_COMPANY.
        Only called on the portal path.
        """
        count = CompanyAccount.objects.filter(company=company).count()
        if count >= CompanyAccountService.MAX_ACCOUNTS_PER_COMPANY:
            raise ValidationError(
                f"Account limit reached. A maximum of "
                f"{CompanyAccountService.MAX_ACCOUNTS_PER_COMPANY} accounts "
                f"are allowed per company."
            )

    @staticmethod
    def get_account_stats(company):
        """
        Returns account stats for a company — used by the portal manage accounts page.
        Returns dict: total, approved, pending, remaining slots, limit.
        """
        accounts = CompanyAccount.objects.filter(company=company)
        total = accounts.count()
        approved = accounts.filter(is_approved=True).count()
        pending = total - approved
        remaining = max(0, CompanyAccountService.MAX_ACCOUNTS_PER_COMPANY - total)
        return {
            'total': total,
            'approved': approved,
            'pending': pending,
            'remaining': remaining,
            'limit': CompanyAccountService.MAX_ACCOUNTS_PER_COMPANY,
        }

    @staticmethod
    @transaction.atomic
    def create_company_account(username, password, profile_data, user=None, enforce_limit=False):
        """
        Creates a company staff account atomically:
        1. Validates password strength (if enabled)
        2. Enforces account limit (only when enforce_limit=True — portal path)
        3. Creates Account (is_active=True always; login blocked via is_approved)
        4. Creates CompanyAccount (profile)
        5. Creates UserVerification (2FA row) with TOTP secret

        profile_data must include:
          - 'company'     : Company instance
          - 'is_approved' : True  → admin path, immediately usable
                            False → portal path, pending approval
        enforce_limit=True  → portal path, limit enforced.
        enforce_limit=False → admin path, limit bypassed.
        """
        if not enforce_limit:
            # Admin path — check Django permission
            CompanyAccountService.check_permission(user, 'main_system.add_companyaccount')

        if not username or not password:
            raise ValidationError("Username and password are required.")

        CompanyAccountService._validate_password(password)

        if Account.objects.filter(username=username).exists():
            raise ValidationError(f"Username '{username}' is already taken.")

        company = profile_data.get('company')
        if not company:
            raise ValidationError("A company must be specified for a company account.")

        if enforce_limit:
            CompanyAccountService._check_account_limit(company)

        if profile_data.get('is_primary', False):
            CompanyAccountService._enforce_single_primary(company)

        account = Account.objects.create_user(
            username=username,
            password=password,
        )
        if user:
            account.created_by = user.username
            account.modified_by = user.username
            account.save()

        if user:
            profile_data['created_by'] = user.username
            profile_data['modified_by'] = user.username

        company_account = CompanyAccount.objects.create(
            account=account,
            **profile_data,
        )

        UserVerification.objects.create(
            account=account,
            totp_secret=pyotp.random_base32(),
            is_totp_enabled=False,
        )

        if user:
            AuditLog.create_log(
                action='create',
                target_username=account.username,
                target_type='company_account',
                performed_by=user.username,
                details=json.dumps({
                    'full_name': company_account.full_name,
                    'company': company.company_name,
                    'is_primary': company_account.is_primary,
                    'is_approved': company_account.is_approved,
                })
            )

        return company_account

    @staticmethod
    @transaction.atomic
    def approve_company_account(company_account, user=None):
        """
        Approves a pending company account.
        Sets is_approved=True so the account can log in.
        Approver role and above only.
        """
        CompanyAccountService.check_permission(user, 'main_system.approve_company_account')

        if company_account.is_approved:
            raise ValidationError("This account is already approved.")

        company_account.is_approved = True
        if user:
            company_account.modified_by = user.username
        company_account.save()

        if user:
            AuditLog.create_log(
                action='update',
                target_username=company_account.account.username,
                target_type='company_account',
                performed_by=user.username,
                details=f"Account approved by {user.username}.",
            )

        return company_account

    @staticmethod
    @transaction.atomic
    def update_company_account(company_account, username=None, password=None, profile_data=None, user=None):
        """
        Updates a company staff account.
        - Username change: simple field update (id is PK)
        - Password change: validated then set
        - Profile data: updated on CompanyAccount
        - is_primary: enforced before update
        """
        CompanyAccountService.check_permission(user, 'main_system.change_companyaccount')

        account = company_account.account
        changes = {}

        if username and username != account.username:
            if Account.objects.filter(username=username).exclude(id=account.id).exists():
                raise ValidationError(f"Username '{username}' is already taken.")
            changes['username'] = {'old': account.username, 'new': username}
            account.username = username

        if password:
            CompanyAccountService._validate_password(password)
            account.set_password(password)
            changes['password'] = 'changed'

        if username or password:
            if user:
                account.modified_by = user.username
            account.save()

        if profile_data:
            if profile_data.get('is_primary', False):
                CompanyAccountService._enforce_single_primary(
                    company_account.company,
                    exclude_account=account,
                )

            for field, new_value in profile_data.items():
                if field in ['created_by']:
                    continue
                old_value = getattr(company_account, field, None)
                if str(old_value) != str(new_value):
                    changes[field] = {'old': str(old_value), 'new': str(new_value)}
                setattr(company_account, field, new_value)

            if user:
                company_account.modified_by = user.username
            company_account.save()

        if changes and user:
            AuditLog.create_log(
                action='update',
                target_username=account.username,
                target_type='company_account',
                performed_by=user.username,
                details=json.dumps(changes),
            )

        return company_account

    @staticmethod
    @transaction.atomic
    def soft_delete_company_account(company_account, user=None):
        """Soft deletes a single company staff account. Sets account.is_active=False."""
        CompanyAccountService.check_permission(user, 'main_system.soft_delete_company_account')

        account = company_account.account
        account.is_active = False
        if user:
            account.modified_by = user.username
        account.save()

        if user:
            company_account.modified_by = user.username
            company_account.save()

            AuditLog.create_log(
                action='soft_delete',
                target_username=account.username,
                target_type='company_account',
                performed_by=user.username,
                details=f"Company account '{account.username}' soft deleted.",
            )

        return company_account

    @staticmethod
    @transaction.atomic
    def hard_delete_company_account(company_account, user=None):
        """Hard deletes a company staff account. Cascade handles profile + verification rows."""
        CompanyAccountService.check_permission(user, 'main_system.delete_companyaccount')

        account = company_account.account
        username = account.username
        full_name = company_account.full_name

        if user:
            AuditLog.create_log(
                action='hard_delete',
                target_username=username,
                target_type='company_account',
                performed_by=user.username,
                details=json.dumps({
                    'username': username,
                    'full_name': full_name,
                    'company': company_account.company.company_name,
                })
            )

        account.delete()
        return True

    @staticmethod
    @transaction.atomic
    def reset_password(company_account, new_password, user=None):
        """Resets password for a company staff account."""
        account = company_account.account

        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required.")
        if not user.is_superuser:
            user_groups = list(user.groups.values_list('name', flat=True))
            if user.username == account.username:
                raise PermissionDenied("You cannot reset your own password through this service.")
            if 'Editor' in user_groups and account.is_staff:
                raise PermissionDenied("Editors cannot reset staff account passwords.")

        CompanyAccountService._validate_password(new_password)

        account.set_password(new_password)
        if user:
            account.modified_by = user.username
        account.save()

        if user:
            AuditLog.create_log(
                action='password_reset',
                target_username=account.username,
                target_type='company_account',
                performed_by=user.username,
                details="Password reset via service.",
            )

        return company_account

    @staticmethod
    @transaction.atomic
    def reset_company_account_password(target_company_account, new_password, user=None):
        """
        Allows the primary company account user to reset the password of
        another account belonging to the same company.

        Guards:
          - user must be authenticated
          - user must be a company user with is_primary=True
          - target must belong to the same company as the requester
          - user cannot reset their own password via this method
        """
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required.")

        try:
            requester_profile = user.company_profile
        except Exception:
            raise PermissionDenied("No company profile found.")

        if not requester_profile.is_primary:
            raise PermissionDenied("Only the primary account user can reset passwords.")

        target_account = target_company_account.account

        if target_account == user:
            raise PermissionDenied("You cannot reset your own password through this action.")

        if target_company_account.company != requester_profile.company:
            raise PermissionDenied("You can only reset passwords for accounts in your own company.")

        CompanyAccountService._validate_password(new_password)

        target_account.set_password(new_password)
        target_account.modified_by = user.username
        target_account.save()

        AuditLog.create_log(
            action='password_reset',
            target_username=target_account.username,
            target_type='company_account',
            performed_by=user.username,
            details=f"Password reset by primary user '{user.username}'.",
        )

        return target_company_account


# ============================================================
# VERIFICATION INTERNAL HELPERS
# ============================================================

def _hash_otp(plain_otp: str) -> str:
    return hashlib.sha256(plain_otp.encode()).hexdigest()


def _check_otp(plain_otp: str, stored: str) -> bool:
    if getattr(settings, 'HASH_OTP', True):
        return _hash_otp(plain_otp) == stored
    return plain_otp == stored


def _is_timed_out(record: UserVerification) -> tuple[bool, str]:
    """Returns (is_timed_out, message)."""
    if record.timeout_until and timezone.now() < record.timeout_until:
        remaining = (record.timeout_until - timezone.now()).seconds // 60
        return True, f"Too many failed attempts. Try again in {remaining} minute(s)."
    return False, ""


def _handle_failed_attempt(record: UserVerification) -> tuple[bool, str]:
    """Increments failed_attempts and applies timeout if threshold reached."""
    record.failed_attempts += 1
    max_attempts = getattr(settings, 'OTP_MAX_ATTEMPTS', 3)

    if record.failed_attempts >= max_attempts:
        timeout_minutes = getattr(settings, 'OTP_TIMEOUT_MINUTES', 15)
        record.timeout_until = timezone.now() + timedelta(minutes=timeout_minutes)
        record.save()
        return True, f"Too many failed attempts. You are locked out for {timeout_minutes} minute(s)."

    record.save()
    remaining_attempts = max_attempts - record.failed_attempts
    return False, f"Invalid code. {remaining_attempts} attempt(s) remaining."


def _reset_verification_state(record: UserVerification) -> None:
    """Resets failed attempts and timeout on successful verification."""
    record.failed_attempts = 0
    record.timeout_until = None
    record.save()


# ============================================================
# TOTP — AUTHENTICATOR APP
# ============================================================

def get_totp_qr_uri(user) -> str:
    """Returns the TOTP provisioning URI for QR code generation."""
    record = user.user_verification

    if not record.totp_secret:
        record.totp_secret = pyotp.random_base32()
        record.save()

    totp = pyotp.TOTP(record.totp_secret)
    return totp.provisioning_uri(
        name=user.username,
        issuer_name="RJBCL-CorporatePortal",
    )


def verify_totp(user, code: str) -> tuple[bool, str]:
    """
    Verifies a TOTP code from the authenticator app.
    Uses valid_window=1 to tolerate ±30s clock drift.
    Prevents replay attacks via last_used_step.
    """
    try:
        record = user.user_verification
    except UserVerification.DoesNotExist:
        return False, "Verification record not found."

    timed_out, message = _is_timed_out(record)
    if timed_out:
        return False, message

    totp = pyotp.TOTP(record.totp_secret)
    current_step = int(timezone.now().timestamp()) // 30

    if record.last_used_step is not None and current_step == record.last_used_step:
        return False, "Code already used. Please wait for the next code."

    if not totp.verify(code, valid_window=1):
        _, message = _handle_failed_attempt(record)
        return False, message

    record.last_used_step = current_step
    _reset_verification_state(record)

    return True, "TOTP verified successfully."


def setup_totp(user, code: str) -> tuple[bool, str]:
    """
    Verifies TOTP code during first-time QR setup.
    Skips lockout check to avoid locking the user out before TOTP is enabled.
    On success sets is_totp_enabled=True.
    """
    try:
        record = user.user_verification
    except UserVerification.DoesNotExist:
        return False, "Verification record not found."

    if not record.totp_secret:
        record.totp_secret = pyotp.random_base32()
        record.save()

    totp = pyotp.TOTP(record.totp_secret)
    current_step = int(timezone.now().timestamp()) // 30

    if record.last_used_step is not None and current_step == record.last_used_step:
        return False, "Code already used. Please wait for the next code."

    if not totp.verify(code, valid_window=1):
        return False, "Invalid code. Please try again."

    record.is_totp_enabled = True
    record.last_used_step = current_step
    record.failed_attempts = 0
    record.timeout_until = None
    record.save()

    return True, "Authenticator app enabled successfully."


# ============================================================
# SMS OTP — FALLBACK
# ============================================================

def generate_otp(user) -> str:
    """
    Issues a new OTP for the user.
    Sets otp_created_at explicitly for expiry checks.
    Resets failed_attempts and timeout_until.
    Returns plain OTP (caller sends via SMS).
    """
    plain_otp = "123456"  # TODO: replace with random generation + SparrowSMS

    otp_value = _hash_otp(plain_otp) if getattr(settings, 'HASH_OTP', True) else plain_otp

    record = user.user_verification
    record.otp_hash = otp_value
    record.otp_created_at = timezone.now()
    record.failed_attempts = 0
    record.timeout_until = None
    record.save()

    return plain_otp


def verify_otp(user, plain_otp: str) -> tuple[bool, str]:
    """
    Verifies the SMS OTP for the given user.
    Uses otp_created_at for expiry (not created_at).
    Returns (success, message).
    """
    try:
        record = user.user_verification
    except UserVerification.DoesNotExist:
        return False, "Verification record not found."

    timed_out, message = _is_timed_out(record)
    if timed_out:
        return False, message

    if not record.otp_created_at:
        return False, "No OTP has been generated. Please request a new one."

    expire_seconds = getattr(settings, 'OTP_EXPIRE_SECONDS', 120)
    if timezone.now() > record.otp_created_at + timedelta(seconds=expire_seconds):
        return False, "OTP has expired. Please request a new one."

    if not _check_otp(plain_otp, record.otp_hash):
        _, message = _handle_failed_attempt(record)
        return False, message

    _reset_verification_state(record)
    return True, "OTP verified successfully."