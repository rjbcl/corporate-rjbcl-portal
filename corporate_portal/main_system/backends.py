from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from .models import AccountLockout

Account = get_user_model()

class CustomAuthBackend(ModelBackend):
    '''
    Authentication backend with lockout enforcement and company_code validation.
    
    Flow:
    1. Check lockout status. (If locked, reject).
    2. Fetch User. (If user doesn't exist, increment lockout, reject).
    3. Check Password. (If wrong, increment lockout, reject).
    4. Check Company Code for company users. (If wrong, reject WITHOUT incrementing lockout).
    5. Check if user is active. (If inactive, reject).
    6. Return user. View redirects to 2FA or dashboard.
    7. Lockout counter is reset ONLY after full login completion (or 2FA).
    '''
    def authenticate(self, request, username=None, password=None, company_code=None, **kwargs):
        if not username:
            return None
        
        normalized_username = username.lower()
        lockout, _ = AccountLockout.objects.get_or_create(username=normalized_username)
        
        # 1. Reject if currently locked
        if lockout.is_locked():
            return None
        
        # 2. Fetch user (case-insensitive to match Django's default behavior)
        try:
            user = Account.objects.get(username__iexact=username)
        except Account.DoesNotExist:
            # Anti-enumeration: register failure for non-existent users too
            lockout.register_failure()
            return None
        except Account.MultipleObjectsReturned:
            return None

        # 3. Check password
        if user.check_password(password):
            # Password is correct!
            
            # 4. Check company_code ONLY for company users
            if user.get_user_type() == 'company':
                if not self._verify_company_code(user, company_code):
                    # Requirement #7: Wrong company code does NOT count as a failed attempt
                    return None
            
            # 5. Check if user is active (Django standard practice)
            if not self.user_can_authenticate(user):
                return None
            
            # NOTE: Per requirement #4, we DO NOT reset the lockout counter here.
            # The counter is only reset after the full flow completes (in the view/2FA).
            return user
        else:
            # Wrong password -> register failure
            lockout.register_failure()
            return None

    def _verify_company_code(self, user, company_code):
        """
        Verifies if the provided company_code matches the user's associated company.
        """
        if not company_code:
            return False
            
        try:
            user_company_code = user.company_profile.company.company_code
            
            if user_company_code is None:
                return False
                
            return str(user_company_code).strip() == str(company_code).strip()
        except AttributeError:
            # Failsafe in case the user doesn't have a company_profile or company linked
            return False