# korean_education_centre/authentication/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [

     # Add these new URL patterns for dashboards
    path('dashboard/', views.dashboard_router, name='dashboard'),  # This will route to the appropriate dashboard
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    
    # Admin Management URLs
    path('admin/students/', views.manage_students, name='manage_students'),
    path('admin/programs/', views.manage_programs, name='manage_programs'),
    path('admin/applications/', views.manage_applications, name='manage_applications'),
    path('admin/activities/', views.manage_activities, name='manage_activities'),
    path('admin/student/<int:student_id>/', views.student_detail, name='student_detail'),
    path('admin/application/<int:application_id>/', views.application_detail, name='application_detail'),
    
    path('admin/logs/', views.admin_logs, name='admin_logs'),
    path('admin/logs/<int:log_id>/', views.log_detail, name='log_detail'),
    path('admin/student/<int:student_id>/unlock/', views.unlock_student, name='unlock_student'),
    # Profile URLs
    path('profile/', views.profile_dashboard, name='profile_dashboard'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/security/', views.security_settings, name='security_settings'),
    path('profile/applications/', views.program_applications, name='program_applications'),

    
    path('register/', views.register, name='register'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('login/', auth_views.LoginView.as_view(template_name='authentication/login.html',
        redirect_authenticated_user=True), name='login'),

    path('logout/', auth_views.LogoutView.as_view(
        template_name='authentication/logout.html',
        next_page='home'
    ), name='logout'),



    path('profile/update/', views.update_profile, name='update_profile'),
    
    path('2fa/setup/', views.setup_2fa, name='setup_2fa'),

    path('2fa/verify/', views.verify_2fa, name='verify_2fa'),

    path('password/change/', views.change_password, name='change_password'),

    path('profile/', views.profile, name='profile'),

    path('profile/deactivate/', views.deactivate_account, name='deactivate_account'),

    # password Reset 
    path('password/reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='authentication/password_reset.html'
         ), 
         name='password_reset'),
    path('password/reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='authentication/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='authentication/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    path('password/reset/complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='authentication/password_reset_complete.html'
         ), 
         name='password_reset_complete'),

    
   

    # Other existing URLs...
]

