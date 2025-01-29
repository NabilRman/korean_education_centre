#korean_education_centre/core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage, EmptyPage
from .models import Program, Activity, ProgramApplication
from .forms import ProgramApplicationForm, ActivityForm, ProgramForm, ContactForm
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import PermissionDenied
from authentication.decorators import student_required, admin_required
from authentication.utils import verify_phone_code, send_phone_verification, log_system_event
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import ContactInquiry
from .forms import ContactForm

def home(request):
    """Home page view showing latest activities and programs."""
    activities = Activity.objects.filter(is_active=True)[:3]
    programs = Program.objects.filter(is_active=True)[:3]
    return render(request, 'home/home.html', {
        'activities': activities,
        'programs': programs
    })

def about(request):
    """About page view."""
    return render(request, 'home/about.html')

def programs(request):
    """Programs listing page."""
    programs = Program.objects.filter(is_active=True)
    return render(request, 'home/programs.html', {'programs': programs})

def program_detail(request, program_id):
    """Individual program detail view."""
    program = get_object_or_404(Program, id=program_id, is_active=True)
    return render(request, 'home/program_detail.html', {'program': program})

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

def activities(request):
   activities_list = Activity.objects.filter(is_active=True).order_by('-published_date')
   paginator = Paginator(activities_list, 9) 
   
   try:
       page = request.GET.get('page', 1)
       activities = paginator.page(page)
   except PageNotAnInteger:
       activities = paginator.page(1)
   except EmptyPage:
       activities = paginator.page(paginator.num_pages)
   
   return render(request, 'home/activities.html', {'activities': activities})

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            inquiry = form.save()
            
            # Send email notification to admin
            context = {
                'inquiry': inquiry,
            }
            html_message = render_to_string('home/contact_notification.html', context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                f'New Contact Inquiry: {inquiry.subject}',
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],  # Add this to settings.py
                html_message=html_message
            )
            
            messages.success(request, 'Your message has been sent successfully. We will contact you soon.')
            return redirect('contact')
    else:
        initial = {}
        if request.user.is_authenticated:
            initial = {
                'name': request.user.get_full_name(),
                'email': request.user.email
            }
        form = ContactForm(initial=initial)
    
    return render(request, 'home/contact.html', {'form': form})


@login_required
@student_required
@csrf_protect
def apply_program(request, program_id):
    """Handle program application submission."""
    program = get_object_or_404(Program, id=program_id, is_active=True)
    student = request.user.student
    
    if request.method == 'POST':
        form = ProgramApplicationForm(request.POST, request.FILES, student=student,)
        if form.is_valid():
            application = form.save(commit=False)
            application.student = student
            application.program = program
            application.save()

            log_system_event(
                request,
                category='application',
                action=f'New program application submitted',
                details={
                    'program_id': program.id,
                    'program_name': program.name,
                    'application_id': application.id
                }
            )

            messages.success(request, 'Your application has been submitted successfully.')
            return redirect('program_applications')
    else:
        form = ProgramApplicationForm(student=student, initial={'program': program})
    
    return render(request, 'home/apply_program.html', {
        'form': form,
        'program': program
    })

@login_required
@admin_required
def manage_programs(request):
    """Admin view for managing programs."""
    if request.method == 'POST':
        form = ProgramForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()

            messages.success(request, 'Program created successfully.')
            return redirect('manage_programs')
    else:
        form = ProgramForm()
    
    programs = Program.objects.all().order_by('-created_at')
    return render(request, 'admin/manage_programs.html', {
        'form': form,
        'programs': programs
    })

@login_required
@admin_required
def manage_activities(request):
    """Admin view for managing activities."""
    if request.method == 'POST':
        form = ActivityForm(request.POST, request.FILES)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.posted_by = request.user
            activity.save()
            messages.success(request, 'Activity created successfully.')
            return redirect('manage_activities')
    else:
        form = ActivityForm()
    
    activities = Activity.objects.all().order_by('-published_date')
    return render(request, 'admin/manage_activities.html', {
        'form': form,
        'activities': activities
    })