# korean_education_centre/authentication/apps.py
from django.apps import AppConfig
class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'


    def ready(self):
        from .groups import create_default_groups
        create_default_groups()