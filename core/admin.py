# korean_education_centre/core/admin.py
from django.contrib import admin
from .models import Student, Program, ProgramApplication, Activity
from .models import ContactInquiry

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'user', 'phone_number', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('student_id', 'user__username', 'user__email', 'phone_number')
    date_hierarchy = 'created_at'

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'program_type', 'start_date', 'end_date', 'is_active')
    list_filter = ('program_type', 'is_active', 'start_date')
    search_fields = ('name', 'description')
    date_hierarchy = 'created_at'

@admin.register(ProgramApplication)
class ProgramApplicationAdmin(admin.ModelAdmin):
    list_display = ('student', 'program', 'status', 'application_date', 'reviewed_by')
    list_filter = ('status', 'application_date')
    search_fields = ('student__user__username', 'program__name')
    date_hierarchy = 'application_date'

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'posted_by', 'published_date', 'is_active')
    list_filter = ('is_active', 'published_date')
    search_fields = ('title', 'content')
    date_hierarchy = 'published_date'
# Register your models here.

@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'inquiry_type', 'created_at', 'is_read', 'is_responded')
    list_filter = ('inquiry_type', 'is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at', 'ip_address', 'user_agent')
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone', 'inquiry_type')
        }),
        ('Inquiry Details', {
            'fields': ('subject', 'message', 'created_at')
        }),
        ('Response', {
            'fields': ('response', 'responded_by', 'responded_at')
        }),
        ('Tracking', {
            'fields': ('is_read', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        })
    )

    def save_model(self, request, obj, form, change):
        if change and 'response' in form.changed_data:
            obj.add_response(request.user, obj.response)
        super().save_model(request, obj, form, change)

    def is_responded(self, obj):
        return obj.is_responded
    is_responded.boolean = True
    is_responded.short_description = 'Responded'