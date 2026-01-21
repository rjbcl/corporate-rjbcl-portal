from django.db import models #type: ignore


class GroupInformation(models.Model):
    """
    Read-only model for tblGroupInformation from external company database.
    This is an unmanaged model - Django will not create/modify this table.
    """
    row_id = models.BigAutoField(
        db_column='RowId',
        primary_key=True
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
    discount_rate = models.DecimalField(
        db_column='DiscountRate',
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
    short_name = models.CharField(
        db_column='ShortName',
        max_length=50,
        null=True,
        blank=True
    )
    master_policy_no = models.CharField(
        db_column='MasterPolicyNo',
        max_length=50,
        null=True,
        blank=True
    )
    group_id = models.CharField(
        db_column='GroupId',
        max_length=50,
        null=True,
        blank=True
    )
    created_by = models.CharField(
        db_column='CreatedBy',
        max_length=50,
        null=True,
        blank=True
    )
    created_date = models.DateTimeField(
        db_column='CreatedDate',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(
        db_column='IsActive',
        null=True,
        blank=True
    )
    group_type = models.CharField(
        db_column='GroupType',
        max_length=100,
        null=True,
        blank=True
    )
    account_number = models.BigIntegerField(
        db_column='AccountNumber',
        null=True,
        blank=True
    )
    p_seq = models.CharField(
        db_column='PSeq',
        max_length=50,
        null=True,
        blank=True
    )
    g_seq = models.CharField(
        db_column='Gseq',
        max_length=50,
        null=True,
        blank=True
    )
    modified_by = models.CharField(
        db_column='ModifiedBy',
        max_length=50,
        null=True,
        blank=True
    )
    modified_date = models.DateTimeField(
        db_column='ModifiedDate',
        null=True,
        blank=True
    )
    r_seq = models.IntegerField(
        db_column='RSeq',
        null=True,
        blank=True
    )
    plan_id = models.IntegerField(
        db_column='PlanID',
        null=True,
        blank=True
    )
    adb_discount_rate = models.DecimalField(
        db_column='ADBDiscountRate',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    retirement_age = models.IntegerField(
        db_column='RetirementAge',
        null=True,
        blank=True
    )
    min_age = models.BigIntegerField(
        db_column='MinAge',
        null=True,
        blank=True
    )
    max_age = models.BigIntegerField(
        db_column='MaxAge',
        null=True,
        blank=True
    )
    min_term = models.BigIntegerField(
        db_column='MinTerm',
        null=True,
        blank=True
    )
    max_term = models.BigIntegerField(
        db_column='MaxTerm',
        null=True,
        blank=True
    )
    rebate = models.IntegerField(
        db_column='Rebate',
        null=True,
        blank=True
    )
    p2_seq = models.BigIntegerField(
        db_column='P2Seq',
        null=True,
        blank=True
    )
    doc = models.DateTimeField(
        db_column='DOC',
        null=True,
        blank=True
    )
    g_loan = models.CharField(
        db_column='G_LOAN',
        max_length=10,
        null=True,
        blank=True
    )
    s_policy = models.CharField(
        db_column='S_Policy',
        max_length=50,
        null=True,
        blank=True
    )
    adb_amount = models.DecimalField(
        db_column='ADBAmount',
        max_digits=19,
        decimal_places=4,
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
    mode = models.CharField(
        db_column='Mode',
        max_length=50,
        null=True,
        blank=True
    )
    remarks = models.CharField(
        db_column='Remarks',
        max_length=50,
        null=True,
        blank=True
    )
    adb_rate = models.DecimalField(
        db_column='ADBRate',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    extra_load = models.DecimalField(
        db_column='ExtraLoad',
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True
    )
    is_adb = models.CharField(
        db_column='IsADB',
        max_length=10,
        null=True,
        blank=True
    )

    class Meta:
        managed = False  # Django won't create/modify this table
        db_table = 'tblGroupInformation'  # Exact table name in external DB
        ordering = ['-created_date']  # Optional: default ordering

    def __str__(self):
        return f"{self.group_name or 'Unnamed Group'} ({self.group_id or 'No ID'})"
    
class GroupEndowment(models.Model):
    """
    Read-only model for view_copo_groupEndowment.
    This view combines tblGroupEndowment and tblGroupEndowmentDetails,
    prioritizing more reliable data from tblGroupEndowmentDetails.
    """
    # Primary Keys (composite)
    register_no = models.CharField(
        db_column='RegisterNo',
        max_length=50,
        primary_key=True
    )
    policy_no = models.CharField(
        db_column='PolicyNo',
        max_length=50
    )
    
    # Fields from tblGroupEndowmentDetails (prioritized/reliable data)
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
    details_remarks = models.CharField(
        db_column='DetailsRemarks',
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
    age = models.CharField(
        db_column='Age',
        max_length=50,
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
    id_no = models.CharField(
        db_column='IdNo',
        max_length=50,
        null=True,
        blank=True
    )
    id_type = models.CharField(
        db_column='IdType',
        max_length=50,
        null=True,
        blank=True
    )
    appointed_date = models.DateTimeField(
        db_column='AppointedDate',
        null=True,
        blank=True
    )
    endowment_remarks = models.CharField(
        db_column='EndowmentRemarks',
        max_length=200,
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
    previous_policy = models.TextField(
        db_column='PreviousPolicy',
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
    phone_number_residence = models.CharField(
        db_column='PhoneNumberResidence',
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
    approved_date = models.DateTimeField(
        db_column='ApprovedDate',
        null=True,
        blank=True
    )
    approved_by = models.CharField(
        db_column='ApprovedBy',
        max_length=50,
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
    approve_remarks = models.TextField(
        db_column='ApproveRemarks',
        null=True,
        blank=True
    )
    modified_date = models.DateField(
        db_column='ModifiedDate',
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
    is_ind_issue = models.CharField(
        db_column='IsINDIssue',
        max_length=10,
        null=True,
        blank=True
    )
    province_id = models.CharField(
        db_column='ProvinceID',
        max_length=50,
        null=True,
        blank=True
    )
    district_id = models.CharField(
        db_column='DistrictID',
        max_length=50,
        null=True,
        blank=True
    )
    municipality_id = models.CharField(
        db_column='MunicipalityID',
        max_length=50,
        null=True,
        blank=True
    )
    ward_no = models.CharField(
        db_column='WardNo',
        max_length=50,
        null=True,
        blank=True
    )
    age_proof_doc_type = models.IntegerField(
        db_column='AgeProofDocType',
        null=True,
        blank=True
    )
    age_proof_doc_no = models.CharField(
        db_column='AgeProofDocNo',
        max_length=50,
        null=True,
        blank=True
    )
    nep_address = models.CharField(
        db_column='NepAddress',
        max_length=50,
        null=True,
        blank=True
    )
    nep_father_name = models.CharField(
        db_column='NepFatherName',
        max_length=50,
        null=True,
        blank=True
    )
    nep_mother_name = models.CharField(
        db_column='NepMotherName',
        max_length=50,
        null=True,
        blank=True
    )
    nep_nominee_name = models.CharField(
        db_column='NepNomineeName',
        max_length=50,
        null=True,
        blank=True
    )
    nep_nominee_address = models.CharField(
        db_column='NepNomineeAddress',
        max_length=50,
        null=True,
        blank=True
    )
    nom_district_id = models.CharField(
        db_column='NomDistrictID',
        max_length=50,
        null=True,
        blank=True
    )
    nominee_ward_no = models.CharField(
        db_column='NomineeWardNo',
        max_length=50,
        null=True,
        blank=True
    )
    nominee_phone = models.CharField(
        db_column='NomineePhone',
        max_length=50,
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
    terminate_by = models.CharField(
        db_column='TerminateBy',
        max_length=50,
        null=True,
        blank=True
    )
    cancel_date = models.DateField(
        db_column='CancelDate',
        null=True,
        blank=True
    )
    cancel_by = models.CharField(
        db_column='CancelBy',
        max_length=50,
        null=True,
        blank=True
    )
    active_date = models.DateField(
        db_column='ActiveDate',
        null=True,
        blank=True
    )
    active_by = models.CharField(
        db_column='ActiveBy',
        max_length=50,
        null=True,
        blank=True
    )
    terminate_remarks = models.TextField(
        db_column='TerminateRemarks',
        null=True,
        blank=True
    )
    cancel_remarks = models.TextField(
        db_column='CancelRemarks',
        null=True,
        blank=True
    )
    active_remarks = models.TextField(
        db_column='ActiveRemarks',
        null=True,
        blank=True
    )
    lapse_by = models.CharField(
        db_column='LapseBy',
        max_length=50,
        null=True,
        blank=True
    )
    lapse_remarks = models.TextField(
        db_column='LapseRemarks',
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
    


