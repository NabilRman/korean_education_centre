# korean_education_centre/authentication/decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if hasattr(request.user, 'userprofile') and request.user.userprofile.is_admin():
            return function(request, *args, **kwargs)
        messages.error(request, 'You must be an admin to access this page.')
        return redirect('home')
    return wrap

def student_required(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if hasattr(request.user, 'userprofile') and request.user.userprofile.is_student():
            return function(request, *args, **kwargs)
        messages.error(request, 'You must be a student to access this page.')
        return redirect('home')
    return wrap