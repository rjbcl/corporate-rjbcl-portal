from django.db import models  # type: ignore
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager  # type: ignore


# ============================================================
# ABSTRACT BASE
# ============================================================

class AuditBase(models.Model):
    created_by = models.CharField(max_length=30, blank=True, null=True)
    modified_by = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ============================================================
# COMPANY
# ============================================================

class Company(AuditBase):
    """
    Core company record. Created by staff during onboarding.

    Contact person fields (primary_contact_person, primary_person_mobile,
    primary_person_email) are nullable — filled in later by the company's
    primary account user, not by staff at creation time.

    Document/onboarding data lives in CompanyDocument (1:1, separate table).
    """
    company_id = models.AutoField(primary_key=True)
    company_name = models.CharField(max_length=200)
    nepali_name = models.CharField(max_length=200, blank=True, null=True)
    pan_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    telephone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    # Filled in by the primary company account user after login
    primary_contact_person = models.CharField(max_length=200, blank=True, null=True)
    primary_person_mobile = models.CharField(max_length=20, blank=True, null=True)
    primary_person_email = models.EmailField(blank=True, null=True)

    isactive = models.BooleanField(default=True)
    remarks = models.TextField(blank=True, null=True)
    blankcol = models.CharField(max_length=100, blank=True, null=True)  # Placeholder for future use

    class Meta:
        db_table = 'copo_company'
        permissions = [
            ('soft_delete_company', 'Can soft delete company'),
        ]

    def __str__(self):
        return self.company_name


# ============================================================
# ACCOUNT
# ============================================================

class AccountManager(BaseUserManager):

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)


class Account(AbstractBaseUser, PermissionsMixin, AuditBase):
    """
    Central auth table for all user types: admin, staff, company.
    username is unique but NOT the primary key — id is.
    Company-specific profile data lives in CompanyAccount (1:1).
    """
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = AccountManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'copo_accounts'
        permissions = [
            ('view_own_account', 'Can view own account details'),
            ('reset_staff_password', 'Can reset staff passwords'),
        ]

    def __str__(self):
        return self.username

    def get_user_type(self):
        """Returns 'admin', 'staff', or 'company'."""
        if self.is_superuser:
            return 'admin'
        if self.is_staff:
            return 'staff'
        if hasattr(self, 'company_profile'):
            return 'company'
        return None

    def get_display_name(self):
        """Returns the appropriate display name based on user type."""
        if self.get_user_type() == 'company':
            return self.company_profile.full_name or self.username
        return self.username

    def has_perm(self, perm, obj=None):
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        return super().has_module_perms(app_label)


# ============================================================
# COMPANY ACCOUNT (company staff profile)
# ============================================================

class CompanyAccount(AuditBase):
    """
    Profile table for company-type users.
    One row per company staff account (1:1 with Account).
    Multiple staff can belong to one company (M:1 with Company).
    is_primary flags the main contact person for a company —
    enforced at the service layer (only one per company).
    """
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='company_profile',
        db_column='account_id',
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='company_accounts',
        db_column='company_id',
    )
    full_name = models.CharField(max_length=200, blank=True, null=True)
    mobile = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)

    class Meta:
        db_table = 'copo_company_accounts'
        permissions = [
            ('soft_delete_company_account', 'Can soft delete company account'),
            ('reset_company_account_password', 'Can reset company account passwords'),
            ('approve_company_account', 'Can approve company account'),
        ]

    def __str__(self):
        return f"{self.full_name or self.account.username} — {self.company.company_name}"


# ============================================================
# GROUP
# ============================================================

class Group(AuditBase):
    row_id = models.AutoField(primary_key=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        db_column='company_id',
        related_name='groups',
    )
    group_id = models.CharField(max_length=20, null=True, blank=True, unique=True)
    group_name = models.CharField(max_length=200, null=True, blank=True)
    isdeleted = models.BooleanField(default=False)
    isactive = models.BooleanField(default=True)

    class Meta:
        db_table = 'copo_groups'
        permissions = [
            ('soft_delete_group', 'Can soft delete group'),
        ]

    def __str__(self):
        return self.group_name or f"Group {self.group_id}"


# ============================================================
# COMPANY DOCUMENT (onboarding documents)
# ============================================================

class CompanyDocument(AuditBase):
    """
    Stores onboarding/legal documents for a company.
    1:1 with Company — created only when documents are submitted,
    not at company creation time.

    Inherits AuditBase (created_by, modified_by, created_at, modified_at)
    since admin staff can also edit these records.

    Managed by:
      - Primary company account user via the portal
      - Admin / superuser via Django admin
    """
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='documents',
        db_column='company_id',
    )
    authorized_by = models.CharField(max_length=200, blank=True, null=True)
    business_purpose = models.TextField(blank=True, null=True)
    signature = models.FileField(
        upload_to='company_documents/signatures/',
        blank=True, null=True,
    )
    stamp = models.FileField(
        upload_to='company_documents/stamps/',
        blank=True, null=True,
    )
    official_request_letter = models.FileField(
        upload_to='company_documents/letters/',
        blank=True, null=True,
    )

    class Meta:
        db_table = 'copo_company_documents'
        verbose_name = 'Company Document'
        verbose_name_plural = 'Company Documents'
        permissions = [
            ('view_company_documents', 'Can view company documents'),
        ]

    def __str__(self):
        return f"Documents for {self.company.company_name}"


# ============================================================
# USER VERIFICATION (2FA)
# ============================================================

class UserVerification(models.Model):
    """
    Stores all 2FA verification data for company users.
    One row per account (1:1 with Account).
    Handles both TOTP (authenticator app) and SMS OTP verification.

    Datetime fields:
      created_at     — row creation timestamp, never changes.
      otp_created_at — set explicitly in generate_otp() each time a
                       new OTP is issued. Used for OTP expiry checks.
                       Null until first OTP is generated.
      timeout_until  — set on lockout, cleared on successful verify.
    """
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='user_verification',
        db_column='account_id',
    )
    otp_hash = models.CharField(max_length=255, null=True, blank=True)
    totp_secret = models.CharField(max_length=64, null=True, blank=True)
    is_totp_enabled = models.BooleanField(default=False)
    last_used_step = models.IntegerField(null=True, blank=True)
    failed_attempts = models.IntegerField(default=0)
    timeout_until = models.DateTimeField(null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'copo_user_verification'
        verbose_name = 'User Verification'
        verbose_name_plural = 'User Verifications'

    def __str__(self):
        return f"Verification for {self.account.username}"


# ============================================================
# AUDIT LOG
# ============================================================

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('password_reset', 'Password Reset'),
        ('role_change', 'Role Change'),
        ('soft_delete', 'Soft Delete'),
        ('hard_delete', 'Hard Delete'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('login', 'Login'),
        ('login_failed', 'Login Failed'),
        ('logout', 'Logout'),
        ('permission_change', 'Permission Change'),
    ]
    MAX_LOGS = 20

    log_id = models.AutoField(primary_key=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_username = models.CharField(max_length=100)
    target_type = models.CharField(max_length=50)  # 'account', 'company', 'company_account'
    performed_by = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        db_table = 'copo_audit_log'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} on {self.target_username} by {self.performed_by}"

    @classmethod
    def create_log(cls, action, target_username, target_type, performed_by, details=None, ip_address=None):
        """
        Creates a new audit log entry and enforces the MAX_LOGS cap
        by deleting the oldest entries when the limit is exceeded.
        """
        new_log = cls.objects.create(
            action=action,
            target_username=target_username,
            target_type=target_type,
            performed_by=performed_by,
            details=details,
            ip_address=ip_address,
        )

        total_logs = cls.objects.count()
        if total_logs > cls.MAX_LOGS:
            excess = total_logs - cls.MAX_LOGS
            oldest_ids = list(
                cls.objects.order_by('timestamp')
                .values_list('log_id', flat=True)[:excess]
            )
            cls.objects.filter(log_id__in=oldest_ids).delete()

        return new_log


# ============================================================
# REPORT ACCESS LOG
# ============================================================

class ReportAccessLog(models.Model):
    """
    Audit log that records every report generation attempt —
    both successful and failed — across all corporate report endpoints.
    Stored under 'copo_report_generation_log'.

    A rolling cap of MAX_LOGS rows is enforced: whenever a new log
    is saved, any rows beyond the most recent MAX_LOGS are deleted.
    """

    MAX_LOGS = 50

    class Status(models.TextChoices):
        SUCCESS       = 'success',       'Success'
        NO_DATA       = 'no_data',       'No Data'
        ERROR         = 'error',         'Error'
        FORBIDDEN     = 'forbidden',     'Forbidden'
        INVALID_INPUT = 'invalid_input', 'Invalid Input'

    row_id = models.AutoField(primary_key=True)

    generator = models.CharField(
        max_length=150,
        db_column='generator',
        default='unknown',
        help_text="Username of the user who triggered the report.",
    )
    report_type = models.CharField(
        max_length=150,
        db_index=True,
        help_text="Human-readable report name.",
    )
    query = models.TextField(
        default='N/A',
        help_text="Raw SQL query as executed against the database.",
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        db_index=True,
    )
    has_error = models.BooleanField(default=False)
    error_message = models.TextField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'copo_report_generation_log'
        ordering = ['-generated_at']
        verbose_name = 'Report Generation Log'
        verbose_name_plural = 'Report Generation Logs'

    def __str__(self):
        return f"[{self.generated_at}] {self.generator} → {self.report_type} ({self.status})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        total = ReportAccessLog.objects.count()
        if total > self.MAX_LOGS:
            oldest_ids = list(
                ReportAccessLog.objects
                .order_by('generated_at')
                .values_list('row_id', flat=True)[:total - self.MAX_LOGS]
            )
            ReportAccessLog.objects.filter(row_id__in=oldest_ids).delete()