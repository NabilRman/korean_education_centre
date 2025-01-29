# korean_education_centre/authentication/middleware.py
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render
from axes.handlers.proxy import AxesProxyHandler
from django.contrib.auth.views import LoginView

class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout_minutes = getattr(settings, 'SESSION_TIMEOUT_MINUTES', 30)

    def __call__(self, request):
        if request.user.is_authenticated:
            current_time = timezone.now()
            last_activity = request.session.get('last_activity')

            if last_activity:
                last_activity = timezone.datetime.fromisoformat(last_activity)
                if (current_time - last_activity).total_seconds() / 60 > self.timeout_minutes:
                    logout(request)
                    return redirect(settings.SESSION_TIMEOUT_REDIRECT)

            request.session['last_activity'] = current_time.isoformat()

        response = self.get_response(request)
        return response
    
class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['Referrer-Policy'] = 'strict-origin-same-origin'
        return response

class UserSpecificLockoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/login/' and request.method == 'POST':
            username = request.POST.get('username')
            if username:
                handler = AxesProxyHandler()
                if handler.is_locked(request, {username: username}):
                    return render(request, 'authentication/lockout.html', {
                        'username': username,
                        'cooloff_time': settings.AXES_COOLOFF_TIME
                    })
        return self.get_response(request)
    
