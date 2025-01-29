# korean_education_centre/authentication/views.py
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from authentication.utils import verify_phone_code, send_phone_verification

from django.http import JsonResponse
from django.views.decorators.http import require_POST 

from django.utils import timezone

from core.forms import ProgramApplicationForm
from .forms import (
    StudentRegistrationForm,
    TwoFactorSetupForm,
    TwoFactorVerifyForm,
    CustomPasswordChangeForm,
    ProfileUpdateForm
)

from .models import SystemLog
from core.models import Program, ProgramApplication , Student, Activity # import from core.models
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from .decorators import admin_required, student_required
from .models import UserProfile, EmailVerification, LoginActivity, Session, ConnectedApp
from .utils import log_system_event
from django.contrib.auth.views import LoginView

from axes.conf import settings as axes_settings
from axes.handlers.proxy import AxesProxyHandler
from django.shortcuts import render
from django.contrib.auth.forms import AuthenticationForm as LoginForm
from django.views.decorators.csrf import csrf_protect
import pyotp
import qrcode
import base64
from io import BytesIO
from axes.utils import reset 
from django.http import JsonResponse
from django.db.models import Q

AXES_COOLOFF_TIME = getattr(axes_settings, 'AXES_COOLOFF_TIME', None)




def register(request):
    """Handle student registration with email verification."""
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)

        if form.is_valid():
            # Create user but don't save password yet
            user = form.save(commit=False)
            # Log the event
            log_system_event(
                request,
                category='security',
                action=f'New user registration: {user.email}',
                severity='info',
                details={
                    'email': user.email,
                    'registration_method': 'standard'
                }
            )

            # Set password securely
            user.set_password(form.cleaned_data['password1'])
            user.is_active = False  # Deactivate until email is verified
            user.save()

            
            
            # Create user profile
            profile = UserProfile.objects.create(
                user=user,
                phone_number=form.cleaned_data['phone_number']
            )
            
            # Create email verification token
            token = get_random_string(64)
            EmailVerification.objects.create(user=user, token=token)
            
            # Send verification email
            context = {
                'user': user,
                'verification_url': f"{request.scheme}://{request.get_host()}/verify-email/{token}"
            }
            html_message = render_to_string('authentication/email/verify_email.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                'Verify your email address',
                plain_message,
                settings.EMAIL_HOST_USER,
                [user.email],
                html_message=html_message
            )
            
            messages.success(request, 'Registration successful. Please check your email to verify your account.')
            return redirect('login')
    else:
        form = StudentRegistrationForm()
    
    return render(request, 'authentication/register.html', {'form': form})

def verify_email(request, token):
    """Handle email verification."""
    try:
        verification = EmailVerification.objects.get(token=token)
        if verification.is_valid():
            user = verification.user
            user.is_active = True
            user.save()
            
            profile = user.userprofile
            profile.is_email_verified = True
            profile.save()
            
            verification.delete()
            messages.success(request, 'Email verified successfully. You can now log in.')

            log_system_event(
                request,
                category='security',
                action=f'Email verified for user: {verification.user.email}',
                severity='info'
            )

            return redirect('login')
        else:
            messages.error(request, 'Verification link has expired. Please request a new one.')
    except EmailVerification.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
    
        
        
    return redirect('login')

@login_required
def verify_2fa(request):
    """Handle 2FA verification during login."""
    if request.method == 'POST':
        form = TwoFactorVerifyForm(request.POST)
        if form.is_valid():
            profile = request.user.userprofile
            if profile.verify_2fa(form.cleaned_data['token']):
                login(request)
                # Log successful 2FA verification
                log_system_event(
                    request,
                    category='security',
                    action='2FA verification successful',
                    severity='info'
                )
                return redirect('dashboard')
            messages.error(request, 'Invalid verification code.')
            # Log failed 2FA attempt
            log_system_event(
                request,
                category='security',
                action='2FA verification failed',
                severity='warning'
            )
    else:
        form = TwoFactorVerifyForm()
    
    return render(request, 'authentication/2fa_verify.html', {'form': form})

@login_required
def setup_2fa(request):
    """Handle 2FA setup."""
    if request.method == 'POST':
        form = TwoFactorSetupForm(request.POST)
        if form.is_valid():
            profile = request.user.userprofile
            if profile.verify_2fa(form.cleaned_data['token']):
                profile.is_2fa_enabled = True
                profile.save()
                messages.success(request, '2FA has been enabled successfully.')
                # Log successful 2FA setup
                log_system_event(
                    request,
                    category='security',
                    action='2FA enabled',
                    severity='info'
                )
                return redirect('dashboard')
            messages.error(request, 'Invalid verification code.')
    else:
        form = TwoFactorSetupForm()
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        
        # Generate QR code for 2FA setup
        provisioning_uri = totp.provisioning_uri(
            request.user.email,
            issuer_name="Korean Education Centre"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Create QR code image
        img_buffer = BytesIO()
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(img_buffer, format='PNG')
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        request.session['2fa_secret'] = secret
    
    return render(request, 'authentication/2fa_setup.html', {
        'form': form,
        'qr_code_data': img_str if not request.method == 'POST' else None
    })

@login_required
@require_POST
def verify_2fa_api(request):
    """API endpoint for verifying 2FA token"""
    code = request.POST.get('code')
    secret = request.session.get('2fa_secret')
    
    if not secret:
        return JsonResponse({
            'success': False, 
            'error': 'Setup expired. Please refresh and try again.'
        })
    
    totp = pyotp.TOTP(secret)
    if totp.verify(code):
        profile = request.user.userprofile
        profile.setup_2fa(secret)
        del request.session['2fa_secret']
        return JsonResponse({'success': True})

    return JsonResponse({
        'success': False, 
        'error': 'Invalid verification code'
    })

@login_required
def get_recovery_codes(request):
    """Generate and return new recovery codes."""
    profile = request.user.userprofile
    if not profile.is_2fa_enabled:
        return JsonResponse({'error': '2FA not enabled'}, status=400)
    
    codes = profile.generate_recovery_codes()
    return JsonResponse({'codes': codes})

@login_required
@require_POST
def terminate_session(request, session_id):
    """Terminate a specific session."""
    session = Session.objects.get(pk=session_id)
    if session.user_id != request.user.id:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    session.delete()
    return JsonResponse({'success': True})


@login_required
@require_POST
def revoke_app_access(request, app_id):
    """Revoke access for a connected application."""
    app = ConnectedApp.objects.get(pk=app_id)
    if app.user_id != request.user.id:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    app.delete()
    return JsonResponse({'success': True})


@login_required
def change_password(request):
    """Handle password change."""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Password changed successfully.')
            log_system_event(
                request,
                category='security',
                action='Password changed successfully',
                severity='info'
            )
            return redirect('dashboard')
            
    else:
        form = CustomPasswordChangeForm(request.user)
        log_system_event(
                request,
                category='security',
                action='Password change failed',
                severity='warning',
                details={'errors': form.errors}
            )
    return render(request, 'authentication/change_password.html', {'form': form})

@login_required
def profile(request):
    """Handle profile viewing and updating."""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user.userprofile)
    
    return render(request, 'authentication/profile.html', {'form': form})


@login_required
def profile_dashboard(request):
    """Main profile dashboard view."""
    user = request.user
    profile = user.userprofile
    student = Student.objects.get(user=user)

    # Get recent program applications
    recent_applications = ProgramApplication.objects.filter(
        student__user=user
    ).order_by('-application_date')[:5]
    
    # Get login activity
    login_activity = user.userprofile.loginactivity_set.all().order_by('-timestamp')[:5]
    
    context = {
        'profile': profile,
        'recent_applications': recent_applications,
        'login_activity': login_activity,
        'student': student,
    }
    return render(request, 'authentication/profile.html', context)

@login_required
def update_profile(request):
    """
    This view handles user profile updates. It allows users to modify their personal
    information while ensuring data validation and security.
    """
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user.userprofile)
        if form.is_valid():
            # Update the user's basic information
            user = request.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            
            
            # Update the profile-specific information
            profile = form.save(commit=False)
            profile.user = user
            profile.save()

            log_system_event(
                request,
                category='profile',
                action='Profile information updated',
                details={
                    'updated_fields': list(form.changed_data)
                }
            )
            
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('profile_dashboard')
    else:
        # Display the current user's information in the form
        form = ProfileUpdateForm(instance=request.user.userprofile)
    
    return render(request, 'authentication/update_profile.html', {
        'form': form,
        'user': request.user
    })

@login_required
def program_applications(request):
    
    student = Student.objects.get(user=request.user)
    applications = ProgramApplication.objects.filter(
        student=student
    ).order_by('-application_date')
    
       
    
    return render(request, 'authentication/program_applications.html', {
        'applications': applications
    })

@login_required
def login_activity(request):
    """View for detailed login activity history."""
    activity = LoginActivity.objects.filter(
        user_profile=request.user.userprofile
    ).order_by('-login_datetime')
    return render(request, 'settings/security/login_activity.html', {'activity': activity})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            log_system_event(
                request,
                category='login',
                action='User logged in successfully',
                details={
                    'username': user.username,
                    'login_method': '2FA' if user.userprofile.is_2fa_enabled else 'standard'
                }
            )
@login_required
def security_settings(request):
    """View and manage security settings."""
    profile = request.user.userprofile
    
    context = {
        'login_activity': LoginActivity.objects.filter(
            user_profile=request.user.userprofile
        ).order_by('-login_datetime')[:5],
        
        'active_sessions': Session.get_user_sessions(request.user),  # Fixed this line
        'connected_apps': ConnectedApp.objects.filter(user=request.user),

        'is_2fa_enabled': profile.is_2fa_enabled,
        'last_password_change': request.user.password_changed_at if hasattr(request.user, 'password_changed_at') else None,
        'email_verified': profile.is_email_verified,
    }
    return render(request, 'authentication/security_settings.html', context)

@login_required
def two_factor_settings(request):
    """Two-factor authentication settings view."""
    return render(request, 'settings/security/two_factor.html')

@login_required
def change_phone_number(request):
    """Handle phone number updates with verification."""
    if request.method == 'POST':
        new_phone = request.POST.get('phone_number')
        verification_code = request.POST.get('verification_code')
        
        if verification_code:
            # Verify the code
            if verify_phone_code(request.user, verification_code):
                profile = request.user.userprofile
                profile.phone_number = profile.pending_phone_number
                profile.pending_phone_number = None
                profile.save()
                messages.success(request, 'Phone number updated successfully.')
                return redirect('security_settings')
            messages.error(request, 'Invalid verification code.')
        else:
            # Send verification code
            send_phone_verification(request.user, new_phone)
            messages.info(request, 'Verification code sent to your new phone number.')
            
    return render(request, 'authentication/change_phone.html')

@login_required
def notification_settings(request):
    """Handle notification preferences."""
    profile = request.user.userprofile
    
    if request.method == 'POST':
        profile.email_notifications = request.POST.get('email_notifications') == 'on'
        profile.sms_notifications = request.POST.get('sms_notifications') == 'on'
        profile.application_updates = request.POST.get('application_updates') == 'on'
        profile.save()
        messages.success(request, 'Notification settings updated successfully.')
        return redirect('notification_settings')
    
    return render(request, 'authentication/notification_settings.html', {
        'profile': profile
    })

@login_required
def deactivate_account(request):
    """Handle account deactivation."""
    if request.method == 'POST':
        password = request.POST.get('password')
        if request.user.check_password(password):
            user = request.user
            user.is_active = False
            user.save()
            messages.success(request, 'Your account has been deactivated.')
            return redirect('logout')
        messages.error(request, 'Invalid password.')
    
    return render(request, 'authentication/deactivate_account.html')

@login_required
def dashboard_router(request):
    """Route users to appropriate dashboard based on their role."""
    try:
        if request.user.userprofile.is_admin():
            return redirect('admin_dashboard')
        else:
            return redirect('student_dashboard')
    except Exception:
        messages.error(request, 'Profile not properly configured. Please contact support.')
        return redirect('home')

@login_required
@admin_required
def admin_dashboard(request):
    """Admin dashboard view."""
    context = {
        'pending_applications': ProgramApplication.objects.filter(status='PENDING').count(),
        'total_students': Student.objects.filter(is_active=True).count(),
        # Add other admin-specific data as needed
    }
    return render(request, 'authentication/admin_dashboard.html', context)

@login_required
@student_required
def student_dashboard(request):
    """Student dashboard view."""
    try:
        student = Student.objects.get(user=request.user)
        applications = ProgramApplication.objects.filter(student=student)
        context = {
            'student': student,
            'applications': applications,
            'pending_applications': applications.filter(status='PENDING').count(),
            'approved_applications': applications.filter(status='APPROVED').count(),
        }
        return render(request, 'authentication/student_dashboard.html', context)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found. Please contact support.')
        return redirect('home')

@login_required
@admin_required
def manage_students(request):
    """View for managing all students."""
    students = Student.objects.all().order_by('-created_at')
    search_query = request.GET.get('search', '')
    
    if search_query:
        students = students.filter(
            Q(user_email_icontains=search_query) | students.filter,
            Q(student_id__icontains=search_query) | students.filter,
            Q(user_first_name_icontains=search_query) | students.filter,
            Q(user_last_name_icontains=search_query)
        )

    paginator = Paginator(students, 10)
    page = request.GET.get('page')
    students = paginator.get_page(page)
    
    log_system_event(
            request,
            category='admin',
            action=f'Student status changed: {students.user.email}',
            severity='info',
            details={
                'student_id': students.id,
                'new_status': 'active' if students.is_active else 'inactive',
                'changed_by': request.user.username
            }
        )
    
    return render(request, 'admin/manage_students.html', {
        'students': students,
        'search_query': search_query
    })


@login_required
@admin_required
def student_detail(request, student_id):
    """View for student details and editing."""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        # Handle student data update
        student.is_active = request.POST.get('is_active') == 'on'
        student.save()
        
        messages.success(request, 'Student information updated successfully.')
        return redirect('manage_students')
    
    applications = ProgramApplication.objects.filter(student=student)
    return render(request, 'authentication/admin/student_detail.html', {
        'student': student,
        'applications': applications
    })

@login_required
@admin_required
def manage_applications(request):
    """View for managing program applications."""
    applications = ProgramApplication.objects.all().order_by('-application_date')
    status_filter = request.GET.get('status', '')
    
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    paginator = Paginator(applications, 10)
    page = request.GET.get('page')
    applications = paginator.get_page(page)
    
    return render(request, 'authentication/admin/manage_applications.html', {
        'applications': applications,
        'status_filter': status_filter
    })


@login_required
@admin_required
def application_detail(request, application_id):
    """View for application details and processing."""
    application = get_object_or_404(ProgramApplication, id=application_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('notes')
        
        application.status = status
        application.review_notes = notes
        application.reviewed_by = request.user
        application.review_date = timezone.now()
        application.save()
        
        messages.success(request, 'Application has been processed successfully.')
        return redirect('manage_applications')
    
    return render(request, 'authentication/admin/application_detail.html', {
        'application': application
    })

@login_required
@admin_required
def manage_programs(request):
    """View for managing programs."""
    programs = Program.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        # Handle program creation/update
        program_id = request.POST.get('program_id')
        
        if program_id:
            program = get_object_or_404(Program, id=program_id)
        else:
            program = Program()
        
        program.name = request.POST.get('name')
        program.program_type = request.POST.get('program_type')
        program.description = request.POST.get('description')
        program.start_date = request.POST.get('start_date')
        program.end_date = request.POST.get('end_date')
        program.is_active = request.POST.get('is_active') == 'on'
        if request.FILES.get('brochure'):
            program.brochure = request.FILES['brochure']
        
        program.save()
        messages.success(request, 'Program saved successfully.')
        return redirect('manage_programs')
    
    return render(request, 'authentication/admin/manage_programs.html', {
        'programs': programs
    })

@login_required
@admin_required
def manage_activities(request):
    """View for managing activities."""
    activities = Activity.objects.all().order_by('-published_date')
    
    if request.method == 'POST':
        # Handle activity creation/update
        activity_id = request.POST.get('activity_id')
        
        if activity_id:
            activity = get_object_or_404(Activity, id=activity_id)
        else:
            activity = Activity(posted_by=request.user)
        
        activity.title = request.POST.get('title')
        activity.content = request.POST.get('content')

        if request.FILES.get('image'):
            activity.image = request.FILES['image']
        
        activity.is_active = request.POST.get('is_active') == 'on'
        activity.save()
        
        messages.success(request, 'Activity saved successfully.')
        return redirect('manage_activities')
    
    return render(request, 'authentication/admin/manage_activities.html', {
        'activities': activities
})



@login_required
@admin_required
def admin_logs(request):
    """View for displaying system logs with filtering and search capabilities."""
    
    # Get filter parameters from request
    category = request.GET.get('category')
    severity = request.GET.get('severity')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search = request.GET.get('search')
    
    # Start with all logs
    logs = SystemLog.objects.all()
    
    # Apply filters
    if category:
        logs = logs.filter(category=category)
    if severity:
        logs = logs.filter(severity=severity)
    if date_from:
        logs = logs.filter(timestamp__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__lte=date_to)
    if search:
        logs = logs.filter(action__icontains=search)
    
    # Paginate results
    paginator = Paginator(logs, 50)  # Show 50 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'category_choices': SystemLog.CATEGORY_CHOICES,
        'severity_choices': SystemLog.SEVERITY_CHOICES,
        'selected_category': category,
        'selected_severity': severity,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
    }
    
    return render(request, 'authentication/admin/logs.html', context)

@login_required
@admin_required
def log_detail(request, log_id):
    """API endpoint for getting detailed log information."""
    log = get_object_or_404(SystemLog, id=log_id)
    return JsonResponse({
        'details': log.details,
        'timestamp': log.timestamp.isoformat(),
        'category': log.get_category_display(),
        'severity': log.get_severity_display(),
        'user': log.user.username if log.user else None,
        'ip_address': log.ip_address,
        'user_agent': log.user_agent
    })

# views.py
from django.contrib.auth.views import LoginView
from axes.handlers.proxy import AxesProxyHandler
from django.shortcuts import render

class CustomLoginView(LoginView):
    def form_valid(self, form):
        username = form.cleaned_data.get('username')
        handler = AxesProxyHandler()
        
        if handler.is_locked(self.request, {username: username}):
            return render(self.request, 'authentication/lockout.html', {
                'username': username,
                'cooloff_time': AXES_COOLOFF_TIME
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        response = super().form_invalid(form)
        username = form.cleaned_data.get('username')
        if username:
            handler = AxesProxyHandler()
            if handler.is_locked(self.request, {username: username}):
                return render(self.request, 'authentication/lockout.html', {
                    'username': username,
                    'cooloff_time': AXES_COOLOFF_TIME
                })
        return response
    
@login_required
@student_required
@csrf_protect
def apply_program(request, program_id):
    """Handle program application submission."""
    program = get_object_or_404(Program, id=program_id, is_active=True)
    
    # Check if student profile exists
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found. Please complete your profile first.')
        return redirect('profile_dashboard')
    
    # Check if student profile is complete
    if not student.is_profile_complete():
        messages.warning(request, 'Please complete your profile before applying to programs.')
        return redirect('update_profile')
        
    if request.method == 'POST':
        form = ProgramApplicationForm(request.POST, request.FILES, student=student)
        if form.is_valid():
            try:
                application = form.save(commit=False)
                application.student = student
                application.program = program
                application.save()
                
                messages.success(request, 'Your application has been submitted successfully.')
                return redirect('program_applications')
            except Exception as e:
                messages.error(request, f'Error submitting application: {str(e)}')
                return redirect('programs')
    else:
        form = ProgramApplicationForm(student=student, initial={'program': program})
    
    return render(request, 'home/apply_program.html', {
        'form': form,
        'program': program
    })


@login_required
@admin_required
def unlock_student(request, student_id):
    """Unlock a student account that has been locked due to failed login attempts."""
    try:
        student = Student.objects.get(id=student_id)
        user_profile = student.user.userprofile
        
        # Reset the failed login attempts
        user_profile.failed_login_attempts = 0
        user_profile.last_login_attempt = None
        user_profile.save()
        
        # Reset Axes lockout
        reset(username=student.user.username)
        
        # Log the unlock action
        log_system_event(
            request,
            category='security',
            action=f'Account unlocked for student: {student.user.email}',
            severity='info',
            details={
                'student_id': student.id,
                'unlocked_by': request.user.username
            }
        )
        
        messages.success(request, f'Account unlocked successfully for {student.user.get_full_name()}')
        return JsonResponse({'status': 'success'})
        
    except Student.DoesNotExist:
        messages.error(request, 'Student not found')
        return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)
    except Exception as e:
        messages.error(request, 'Error unlocking account')
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)