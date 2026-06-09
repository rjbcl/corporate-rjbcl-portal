import os
import hashlib
 
from django.db import models  # type: ignore
from main_system.models import Company


class GroupInformation(models.Model):
    """
    Read-only model for view_copo_groupInformation from external company database.
    This view aggregates group information with policy statistics.
    This is an unmanaged model - Django will not create/modify this view.
    """
    # Primary fields from tblGroupInformation
    group_id = models.CharField(
        db_column='GroupId',
        max_length=50,
        primary_key=True  # Using GroupId as primary key since view doesn't have RowId
    )
    group_name = models.CharField(
        db_column='GroupName',
        max_length=50,
        null=True,
        blank=True
    )
    group_name_nepali = models.CharField(
        db_column='GroupNameNepali',
        max_length=50,
        null=True,
        blank=True
    )
    is_active = models.BooleanField(
        db_column='isactive',
        null=True,
        blank=True
    )
    
    # Aggregated statistics from tblGroupEndowmentDetails
    total_members_count = models.IntegerField(
        db_column='Total_members_count',
        null=True,
        blank=True
    )
    total_active_policies = models.IntegerField(
        db_column='Total_active_policies',
        null=True,
        blank=True
    )
    total_premium = models.DecimalField(
        db_column='Total_Premium',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    total_sa = models.DecimalField(
        db_column='Total_SA',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    death_claim = models.IntegerField(
        db_column='Death_Claim',
        null=True,
        blank=True
    )
    surrender_claim = models.IntegerField(
        db_column='Surrender_Claim',
        null=True,
        blank=True
    )
    maturity_claim = models.IntegerField(
        db_column='Maturity_Claim',
        null=True,
        blank=True
    )
    transfer_claim = models.IntegerField(
        db_column='Transfer_Claim',
        null=True,
        blank=True
    )
    terminate_claim = models.IntegerField(
        db_column='Terminate_Claim',
        null=True,
        blank=True
    )
    cancel_claim = models.IntegerField(
        db_column='Cancel_Claim',
        null=True,
        blank=True
    )

    class Meta:
        managed = False  # Django won't create/modify this view
        db_table = 'view_copo_groupInformation'  # Points to the view
        ordering = ['group_id']  # Default ordering by group_id

    def __str__(self):
        return f"{self.group_name or 'Unnamed Group'} ({self.group_id or 'No ID'})"
    
class GroupEndowment(models.Model):
    """
    Read-only model for view_copo_groupEndowment.
    This view combines tblGroupEndowment and tblGroupEndowmentDetails,
    prioritizing more reliable data from tblGroupEndowmentDetails.
    """

    register_no = models.CharField(
        db_column='RegisterNo',
        max_length=50,
        primary_key=True
    )
    policy_no = models.CharField(
        db_column='PolicyNo',
        max_length=50
    )
    group_id = models.CharField(
        db_column='GroupId',
        max_length=50,
        null=True,
        blank=True
    )
    doc = models.DateField(
        db_column='DOC',
        null=True,
        blank=True
    )
    term = models.SmallIntegerField(
        db_column='Term',
        null=True,
        blank=True
    )
    sum_assured = models.DecimalField(
        db_column='SumAssured',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    premium = models.DecimalField(
        db_column='Premium',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    fup = models.DateTimeField(
        db_column='FUP',
        null=True,
        blank=True
    )
    maturity_date = models.DateField(
        db_column='MaturityDate',
        null=True,
        blank=True
    )
    policy_status = models.CharField(
        db_column='PolicyStatus',
        max_length=10,
        null=True,
        blank=True
    )
    policy_type = models.CharField(
        db_column='PolicyType',
        max_length=5,
        null=True,
        blank=True
    )
    late_fine = models.DecimalField(
        db_column='LateFine',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    
    # Unique fields from tblGroupEndowmentDetails
    paid_date = models.DateTimeField(
        db_column='PaidDate',
        null=True,
        blank=True
    )
    instalment = models.SmallIntegerField(
        db_column='Instalment',
        null=True,
        blank=True
    )
    paid_amount = models.DecimalField(
        db_column='PaidAmount',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    batch_no = models.CharField(
        db_column='BatchNo',
        max_length=50,
        null=True,
        blank=True
    )
    intrest = models.DecimalField(
        db_column='Intrest',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    claim_status = models.CharField(
        db_column='ClaimStatus',
        max_length=20,
        null=True,
        blank=True
    )
    late_fine_percent = models.DecimalField(
        db_column='LateFinePercent',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    reduced_instalment = models.IntegerField(
        db_column='ReducedInstalment',
        null=True,
        blank=True
    )
    
    # Fields from tblGroupEndowment (personal/policy details)
    employee_id = models.CharField(
        db_column='EmployeeId',
        max_length=50,
        null=True,
        blank=True
    )
    name = models.CharField(
        db_column='Name',
        max_length=50,
        null=True,
        blank=True
    )
    nep_name = models.CharField(
        db_column='NepName',
        max_length=50,
        null=True,
        blank=True
    )
    gender = models.CharField(
        db_column='Gender',
        max_length=50,
        null=True,
        blank=True
    )
    occupation = models.CharField(
        db_column='Occupation',
        max_length=50,
        null=True,
        blank=True
    )
    dob = models.DateTimeField(
        db_column='DOB',
        null=True,
        blank=True
    )
    extra_premium = models.DecimalField(
        db_column='ExtraPremium',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    total_premium = models.DecimalField(
        db_column='TotalPremium',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    address = models.TextField(
        db_column='Address',
        null=True,
        blank=True
    )
    email = models.CharField(
        db_column='Email',
        max_length=50,
        null=True,
        blank=True
    )
    mobile = models.CharField(
        db_column='Mobile',
        max_length=50,
        null=True,
        blank=True
    )
    adb = models.DecimalField(
        db_column='ADB',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    occ_extra_amount = models.DecimalField(
        db_column='OccExtraAmount',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    adb_discount = models.DecimalField(
        db_column='ADBDiscount',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    father_name = models.CharField(
        db_column='FatherName',
        max_length=50,
        null=True,
        blank=True
    )
    mother_name = models.CharField(
        db_column='MotherName',
        max_length=50,
        null=True,
        blank=True
    )
    nominee_name = models.CharField(
        db_column='NomineeName',
        max_length=50,
        null=True,
        blank=True
    )
    nominee_address = models.CharField(
        db_column='NomineeAddress',
        max_length=50,
        null=True,
        blank=True
    )
    transfer_date = models.DateTimeField(
        db_column='TransferDate',
        null=True,
        blank=True
    )
    duplicate_policy_date = models.DateTimeField(
        db_column='DuplicatePolicyDate',
        null=True,
        blank=True
    )
    lapse_date = models.DateTimeField(
        db_column='LapseDate',
        null=True,
        blank=True
    )
    lapse_active_date = models.DateTimeField(
        db_column='LapseActiveDate',
        null=True,
        blank=True
    )
    doe = models.DateTimeField(
        db_column='DOE',
        null=True,
        blank=True
    )
    basic_premium = models.DecimalField(
        db_column='BasicPremium',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    is_adb = models.CharField(
        db_column='IsADB',
        max_length=1,
        null=True,
        blank=True
    )
    after_dis_rebate_rate = models.DecimalField(
        db_column='AfterDisRebateRate',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    fiscal_year = models.CharField(
        db_column='FiscalYear',
        max_length=50,
        null=True,
        blank=True
    )
    nominee_relationship = models.CharField(
        db_column='NomineeRelationship',
        max_length=100,
        null=True,
        blank=True
    )
    claim_date = models.DateField(
        db_column='ClaimDate',
        null=True,
        blank=True
    )
    termination_date = models.DateField(
        db_column='TerminationDate',
        null=True,
        blank=True
    )
    plan_id = models.SmallIntegerField(
        db_column='PlanId',
        null=True,
        blank=True
    )
    is_multiple_policy_issued = models.BooleanField(
        db_column='IsMultiplePolicyIssued',
        null=True,
        blank=True
    )


    class Meta:
        managed = False
        db_table = 'view_copo_groupEndowment'
        ordering = ['-maturity_date']
        unique_together = [['register_no', 'policy_no']]

    def __str__(self):
        return f"{self.name or 'Unnamed'} - {self.policy_no}"
    
class APIKey(models.Model):
    """
    API key for 3rd party server-to-server authentication.
    One active key per company at any time.
 
    The raw key is shown once at generation and never stored.
    Only the SHA-256 hash is persisted.
 
    Flow:
      1. Superadmin calls APIKey.generate_key(company, created_by)
         → returns raw key (show once), saves hash to DB.
      2. 3rd party sends raw key in X-API-Key header on every request.
      3. APIKeyAuthentication hashes the incoming key and looks up key_hash.
    """
 
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name='api_key',
        db_column='company_id',
    )
    key_hash = models.CharField(max_length=64, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
 
    class Meta:
        db_table = 'copo_api_keys'
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
 
    def __str__(self):
        status = 'active' if self.is_active else 'revoked'
        return f"API Key for {self.company.company_name} ({status})"
 
    @staticmethod
    def _hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()
 
    @classmethod
    def generate_key(cls, company, created_by: str) -> str:
        """
        Generates a new API key for the given company.
        - Blocks generation if company has no primary CompanyAccount.
        - Revokes any existing key before issuing a new one.
        - Returns the raw key (caller must show it once — never retrievable again).
 
        Raises ValueError if no primary account exists for the company.
        """
        from main_system.models import CompanyAccount
 
        primary_exists = CompanyAccount.objects.filter(
            company=company,
            is_primary=True,
            is_approved=True,
        ).exists()
 
        if not primary_exists:
            raise ValueError(
                f"Cannot generate API key for '{company.company_name}': "
                "no approved primary account exists."
            )
 
        # Revoke existing key if present
        cls.objects.filter(company=company).delete()
 
        raw_key = 'copo_' + os.urandom(32).hex()
        key_hash = cls._hash_key(raw_key)
 
        cls.objects.create(
            company=company,
            key_hash=key_hash,
            created_by=created_by,
            is_active=True,
        )
 
        return raw_key
 
    @classmethod
    def lookup(cls, raw_key: str):
        """
        Looks up an APIKey instance by raw key.
        Returns the APIKey instance or None if not found.
        """
        key_hash = cls._hash_key(raw_key)
        try:
            return cls.objects.select_related(
                'company'
            ).get(key_hash=key_hash, is_active=True)
        except cls.DoesNotExist:
            return None



