from django.db import models #type: ignore
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager #type: ignore

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
        permissions = [
            ('view_own_account', 'Can view own account details'),
            ('reset_staff_password', 'Can reset staff passwords'),
        ]
    
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
            ('soft_delete_individual', 'Can soft delete individual'),
            ('reset_individual_password', 'Can reset individual passwords'),
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
    target_type = models.CharField(max_length=50)  # 'account', 'company', 'individual'
    performed_by = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True) 
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    class Meta:
        db_table = 'audit_log'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} on {self.target_username} by {self.performed_by}"
    
    @classmethod
    def create_log(cls, action, target_username, target_type, performed_by, details=None, ip_address=None):
        """
        Create a new audit log and maintain the log limit.
        Automatically deletes oldest logs when limit is exceeded.
        """
        print(f"Creating log: action={action}, target_username={target_username}, target_type={target_type}, performed_by={performed_by}, details={details}, ip_address={ip_address}")
        # Create the new log
        new_log = cls.objects.create(
            action=action,
            target_username=target_username,
            target_type=target_type,
            performed_by=performed_by,
            details=details,
            ip_address=ip_address
        )
        
        # Check if we've exceeded the limit
        total_logs = cls.objects.count()
        if total_logs > cls.MAX_LOGS:
            # Calculate how many to delete
            excess = total_logs - cls.MAX_LOGS
            
            # Get the oldest logs to delete
            oldest_logs = cls.objects.order_by('timestamp')[:excess]
            oldest_log_ids = list(oldest_logs.values_list('log_id', flat=True))
            
            # Delete them
            cls.objects.filter(log_id__in=oldest_log_ids).delete()
        
        return new_log