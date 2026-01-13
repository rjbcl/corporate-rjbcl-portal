from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

class AuditBase(models.Model):
    created_by = models.CharField(max_length=30, blank=True, null=True)
    modified_by = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

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
    username = models.CharField(max_length=100, unique=True, primary_key=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    objects = AccountManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'account'
    
    def __str__(self):
        return self.username
    
    def get_user_type(self):
        """Returns 'staff', 'company', or 'individual'"""
        if self.is_superuser:
            return 'admin'
        
        if self.is_staff:
            return 'staff'
        
        # Check if linked to Company
        if hasattr(self, 'company_profile'):
            return 'company'
        
        # Check if linked to Individual
        if hasattr(self, 'individual_profile'):
            return 'individual'
        
        return None
    
    def get_display_name(self):
        """Returns the appropriate display name based on user type"""
        user_type = self.get_user_type()
        
        if user_type == 'company':
            return self.company_profile.company_name
        elif user_type == 'individual':
            return self.individual_profile.user_full_name or self.username
        else:
            return self.username
        
class Company(AuditBase):
    company_id = models.AutoField(primary_key=True)
    username = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        to_field='username',
        db_column='username',
        related_name='company_profile'
    )
    company_name = models.CharField(max_length=200)
    nepali_name = models.CharField(max_length=200, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    telephone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    isactive = models.BooleanField(default=True)
    remarks = models.TextField(blank=True, null=True)
    blank_col1 = models.CharField(max_length=200, blank=True, null=True)
    blank_col2 = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        db_table = 'company'
        permissions = [
            ('approve_company', 'Can approve company'),
            ('soft_delete_company', 'Can soft delete company'),
        ]

    def __str__(self):
        return self.company_name
    
class Group(AuditBase):
    row_id = models.AutoField(primary_key=True)
    company_id = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        db_column='company_id',
        related_name='groups'
    )
    group_id = models.CharField(max_length=20, null=True, blank=True, unique=True)
    group_name = models.CharField(max_length=200, null=True, blank=True)
    isdeleted = models.BooleanField(default=False)
    isactive = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'groups'
        permissions = [
            ('approve_group', 'Can approve group'),
            ('soft_delete_group', 'Can soft delete group'),
        ]
    
    def __str__(self):
        return self.group_name or f"Group {self.group_id}"

class Individual(AuditBase):
    user_id = models.AutoField(primary_key=True)
    group_id = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        db_column='group_id',
        related_name='individuals'
    )
    username = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        to_field='username',
        db_column='username',
        related_name='individual_profile'
    )
    user_full_name = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = 'individual'
        permissions = [
            ('approve_individual', 'Can approve individual'),
            ('soft_delete_individual', 'Can soft delete individual'),
        ]

    def __str__(self):
        return self.user_full_name or self.username.username
    
class Policy(models.Model):
    row_id = models.AutoField(primary_key=True)
    policy_number = models.CharField(max_length=50, unique=True) 
    user_id = models.ForeignKey(
        'Individual',           
        on_delete=models.CASCADE,  
        db_column='user_id',    
        related_name='policies'
    )

    class Meta:
        db_table = 'policy'

    def __str__(self):
        return f"Policy {self.policy_number} for User {self.user_id_id}"
