from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

Account = get_user_model()

class CompanyCodeBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, company_code=None, **kwargs):
        if company_code:
            # Company user login
            try:
                from main_system.models import Company, CompanyAccount
                company = Company.objects.get(company_code=company_code)
                company_account = CompanyAccount.objects.select_related('account').get(
                    company=company, 
                    account__username=username
                )
                user = company_account.account
            except (Company.DoesNotExist, CompanyAccount.DoesNotExist):
                return None

            if user.check_password(password) and self.user_can_authenticate(user):
                return user
            return None
        
        else:
            # Fallback for Admin and Staff (no company_code provided)
            # Using .filter().first() prevents MultipleObjectsReturned errors 
            # if duplicates somehow exist in the DB.
            user = Account.objects.filter(
                Q(is_superuser=True) | Q(is_staff=True),
                username=username
            ).first()

            if user and user.check_password(password) and self.user_can_authenticate(user):
                return user
            return None