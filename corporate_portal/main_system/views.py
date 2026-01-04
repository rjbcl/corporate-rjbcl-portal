from django.shortcuts import render
from django import forms
from django.http import HttpResponse


class CompanyLoginForm(forms.Form):
    company_id = forms.CharField(
        label="Company ID",
        max_length=20,
        help_text="Enter your unique RJBCL Company ID"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Password"
    )


def home(request):
    if request.method == 'POST':
        form = CompanyLoginForm(request.POST)
        if form.is_valid():
            # For testing purposes only
            return HttpResponse("Form is valid! Crispy forms is working.")
    else:
        form = CompanyLoginForm()

    return render(request, 'index.html', {'form': form})
