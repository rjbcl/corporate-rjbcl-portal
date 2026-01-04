from django.db import models


class Account(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('company', 'Company'),
        ('individual', 'Individual'),
        ('loan', 'Loan'),
    ]
    
    username = models.CharField(max_length=100, primary_key=True)
    password = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)

    class Meta:
        db_table = 'account'

    def __str__(self):
        return self.username


class Company(models.Model):
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
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'company'

    def __str__(self):
        return self.company_name


class Group(models.Model):
    group_id = models.AutoField(primary_key=True)
    company_id = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        db_column='company_id'
    )
    previous_group_id = models.CharField(max_length=200, null=True, blank=True)
    class Meta:
        db_table = 'groups'
    def __str__(self):
        return f"Group {self.group_id}"


class Individual(models.Model):
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