#korean_education_centre/core/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Root URL pattern
    path('home/', views.home, name='home'),  # Alternative home URL
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('programs/', views.programs, name='programs'),
    path('program/<int:program_id>/', views.program_detail, name='program_detail'),
    path('activities/', views.activities, name='activities'),
    path('apply-program/<int:program_id>/', views.apply_program, name='apply_program'),
    
    
]