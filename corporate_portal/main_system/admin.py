from django.contrib import admin
from django import forms
from .models import Company, Group, Individual, Account


class CompanyAdminForm(forms.ModelForm):
    new_username = forms.CharField(max_length=100, required=True)
    new_password = forms.CharField(widget=forms.PasswordInput, required=True)
    previous_group_ids = forms.CharField(
        required=False,
        help_text="Enter comma-separated group IDs (e.g., 101, 102, 103)",
        widget=forms.TextInput(attrs={'placeholder': '101, 102, 103'})
    )

    class Meta:
        model = Company
        fields = ['company_name', 'previous_group_ids']

    def save(self, commit=True):
        # Create Account
        account = Account.objects.create(
            username=self.cleaned_data['new_username'],
            password=self.cleaned_data['new_password'],
            type='company'
        )
        
        # Create Company
        company = super().save(commit=False)
        company.username = account  
        if commit:
            company.save()
            
            # Create Groups
            group_ids = self.cleaned_data.get('previous_group_ids', '')
            if group_ids:
                for gid in group_ids.split(','):
                    gid = gid.strip()
                    if gid:
                        Group.objects.create(
                            company_id=company,
                        )
        
        return company


class IndividualAdminForm(forms.ModelForm):
    new_username = forms.CharField(max_length=100, required=True)
    new_password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = Individual
        fields = ['group_id', 'user_full_name']

    def save(self, commit=True):
        # Create Account
        account = Account.objects.create(
            username=self.cleaned_data['new_username'],
            password=self.cleaned_data['new_password'],
            type='individual'
        )
        
        # Create Individual
        individual = super().save(commit=False)
        individual.username = account
        if commit:
            individual.save()
        
        return individual


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    form = CompanyAdminForm
    list_display = ("username", "company_name")


@admin.register(Individual)
class IndividualAdmin(admin.ModelAdmin):
    form = IndividualAdminForm
    list_display = ("user_full_name", "group_id")



@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("username", "type")