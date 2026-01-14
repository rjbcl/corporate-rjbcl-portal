from django.db import models


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