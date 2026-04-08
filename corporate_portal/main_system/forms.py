from django import forms

class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password     = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean_new_password(self):
        new = self.cleaned_data.get('new_password', '')
        if len(new) < 8:
            raise forms.ValidationError("Password must be at least 8 characters.")
        return new

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('confirm_password'):
            raise forms.ValidationError("New passwords do not match.")
        return cleaned