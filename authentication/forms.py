# korean_education_centre/authentication/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from .models import UserProfile

password_validator = RegexValidator(
    regex=r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{12,}$',
    message='Password must contain at least 12 characters, including letters, numbers, and special characters.'
)

class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')]
    )

    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].validators.append(password_validator)
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        username = self.cleaned_data.get('username')
    
    # Fix the email validation
        if User.objects.exclude(username=username).filter(email=email).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email


class TwoFactorSetupForm(forms.Form):
    token = forms.CharField(
        max_length=6,
        validators=[RegexValidator(regex=r'^\d{6}$')],
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'Enter 6-digit code'
        }),
        help_text='Enter the 6-digit code from your authenticator app'
    )

class TwoFactorVerifyForm(forms.Form):
    token = forms.CharField(
        max_length=6,
        validators=[RegexValidator(regex=r'^\d{6}$')]
    )

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].validators.append(password_validator)

class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be in format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = forms.CharField(validators=[phone_regex], max_length=15)
    emergency_contact = forms.CharField(validators=[phone_regex], max_length=15)

    class Meta:
        model = UserProfile
        fields = ['phone_number', 'emergency_contact']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def clean_email(self):
        email = self.cleaned_data.get('email')
        user = self.instance.user
        if User.objects.exclude(pk=user.pk).filter(email=email).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email