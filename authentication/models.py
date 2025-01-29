# korean_education_centre/authentication/models.py
from datetime import timezone
from django.db import models
from django.contrib.auth.models import User
from django_otp.plugins.otp_totp.models import TOTPDevice
import pyotp

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('student', 'Student'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    is_email_verified = models.BooleanField(default=False)
    is_2fa_enabled = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    last_login_attempt = models.DateTimeField(null=True, blank=True)

    def setup_2fa(self):
        """Set up 2FA for the user"""
        if not self.is_2fa_enabled:
            totp_device = TOTPDevice.objects.create(
                user=self.user,
                name=f"Default device for {self.user.username}",
                confirmed=False
            )
            self.is_2fa_enabled = True
            self.save()
            return totp_device.config_url
        return None

    def verify_2fa(self, token):
        """Verify 2FA token"""
        try:
            totp_device = TOTPDevice.objects.get(user=self.user)
            return totp_device.verify_token(token)
        except TOTPDevice.DoesNotExist:
            return False

    def is_admin(self):
        return self.role == 'admin'

    def is_student(self):
        return self.role =='student'
    
class EmailVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        """Check if verification token is still valid (24 hours)"""
        return (timezone.now() - self.created_at).days < 1

class LoginActivity(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    login_datetime = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    was_successful = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name_plural = 'Login activities'

    def _str_(self):
        return f"{self.user_profile.user.username} - {self.login_datetime}"
    
class Session(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, unique=True)
    device = models.CharField(max_length=200)
    ip_address = models.GenericIPAddressField()
    location = models.CharField(max_length=200, blank=True)
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'

    @property
    def is_current(self):
        """Check if this is the current session"""
        return self.session_key == self.user.session_key

    @classmethod
    def get_user_sessions(cls, user):
        """Get all active sessions for a user"""
        return cls.objects.filter(user=user).order_by('-last_active')

class ConnectedApp(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    client_id = models.CharField(max_length=100, unique=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)
    permissions = models.JSONField(default=dict)

    class Meta:
        verbose_name = 'Connected Application'
        verbose_name_plural = 'Connected Applications'

    def __str__(self):
        return f"{self.name} - {self.user.email}"
    
class SecurityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    action = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    suspicious = models.BooleanField(default=False)

class PasswordHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    password_hash = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

class SecurityAudit(models.Model):
    performed_at = models.DateTimeField(auto_now_add=True)
    findings = models.TextField()
    severity = models.CharField(max_length=20)
    resolved = models.BooleanField(default=False)

# authentication/models.py
class SystemLog(models.Model):
    CATEGORY_CHOICES = (
        ('login', 'Login Activity'),
        ('security', 'Security Event'),
        ('profile', 'Profile Update'),
        ('application', 'Program Application'),
        ('admin', 'Administrative Action'),
    )
    
    SEVERITY_CHOICES = (
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    )

    timestamp = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='info')
    details = models.JSONField(default=dict)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp} - {self.get_category_display()} - {self.action}"

