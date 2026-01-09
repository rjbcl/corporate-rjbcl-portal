from django.db import models


class AuditBase(models.Model):
    created_by = models.CharField(max_length=30, blank=True, null=True)
    modified_by = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Account(AuditBase):
    ACCOUNT_TYPE_CHOICES = [
        ('company', 'Company'),
        ('individual', 'Individual'),
        ('loan', 'Loan'),
    ]
    
    username = models.CharField(max_length=100, primary_key=True)
    password = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)

    class Meta:
        db_table = 'account'

    def __str__(self):
        return self.username


class Company(AuditBase):
    company_id = models.AutoField(primary_key=True)
    username = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        to_field='username',
        db_column='username'
    )
    company_name = models.CharField(max_length=200)
    nepali_name = models.CharField(max_length=200, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    telephone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    isactive = models.BooleanField(default=True)

    class Meta:
        db_table = 'company'

    def __str__(self):
        return self.company_name


class Group(AuditBase):
    row_id = models.AutoField(primary_key=True)
    company_id = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        db_column='company_id'
    )
    group_id = models.CharField(max_length=20, null=True, blank=True, unique=True)
    group_name = models.CharField(max_length=200, null=True, blank=True)  # Add this line
    isdeleted = models.BooleanField(default=False)
    isactive = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'groups'
    
    def __str__(self):
            if self.group_name and self.group_id:
                return f"{self.group_name} ({self.group_id})"
            elif self.group_name:
                return self.group_name
            elif self.group_id:
                return f"Group {self.group_id}"
            return f"Group {self.row_id}"
    


class Individual(AuditBase):
    user_id = models.AutoField(primary_key=True)
    group_id = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        db_column='group_id'
    )
    username = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        to_field='username',
        db_column='username'
    )
    user_full_name = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = 'individual'

    def __str__(self):
        return self.user_full_name or self.username.username