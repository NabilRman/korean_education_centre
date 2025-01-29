# korean_education_centre/authentication/admin.py
from django.contrib import admin
from .models import UserProfile, EmailVerification, LoginActivity

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_email_verified', 'is_2fa_enabled', 'phone_number')
    list_filter = ('role', 'is_email_verified', 'is_2fa_enabled')
    search_fields = ('user__username', 'user__email', 'phone_number')

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__username', 'user__email')
    date_hierarchy = 'created_at'

@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'login_datetime', 'ip_address', 'was_successful')
    list_filter = ('was_successful', 'login_datetime')
    search_fields = ('user_profile__user__username', 'ip_address', 'user_agent')
    date_hierarchy = 'login_datetime'
# Register your models here.
