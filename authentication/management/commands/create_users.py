# authentication/management/commands/create_users.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Student
from authentication.models import UserProfile
from django.utils import timezone

class Command(BaseCommand):
    help = 'Creates initial admin and student users'

    def handle(self, *args, **options):
        # Create Admin User
        try:
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@kec.com',
                password='Admin@123',
                first_name='Admin',
                last_name='User'
            )
            UserProfile.objects.create(
                user=admin_user,
                is_email_verified=True,
                phone_number='+60123456789'
            )
            self.stdout.write(self.style.SUCCESS('Successfully created admin user'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Admin user already exists or error: {str(e)}'))

        # Create Student User
        try:
            student_user = User.objects.create_user(
                username='student',
                email='student@example.com',
                password='Student@123',
                first_name='Student',
                last_name='User'
            )
            UserProfile.objects.create(
                user=student_user,
                is_email_verified=True,
                phone_number='+60123456788'
            )
            Student.objects.create(
                user=student_user,
                student_id='S12345',
                phone_number='+60123456788',
                address='123 Student Street, City',
                date_of_birth=timezone.now().date(),
                emergency_contact='+60123456787'
            )
            self.stdout.write(self.style.SUCCESS('Successfully created student user'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Student user already exists or error: {str(e)}'))