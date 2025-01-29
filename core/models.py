# korean_education_centre/core/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .utils import encrypt_file, decrypt_file
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()
    date_of_birth = models.DateField(null=True, blank=True)
    emergency_contact = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.student_id}"
    
    def is_profile_complete(self):
        """Check if student profile is complete"""
        required_fields = ['phone_number', 'address', 'emergency_contact']
        return all(getattr(self, field) for field in required_fields)


@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    """Create a Student profile when a new user is created"""
    try:
        if created and not hasattr(instance, 'student'):
            # Generate a student ID (you can customize this format)
            student_id = f"STD{instance.id:06d}"
            
            # Wait for UserProfile to be created first
            if hasattr(instance, 'userprofile'):
                phone_number = instance.userprofile.phone_number
            else:
                phone_number = ''
                
            Student.objects.create(
                user=instance,
                student_id=student_id,
                phone_number=phone_number,
                address='',
                emergency_contact=''
            )
    except Exception as e:
        # Log the error but don't break the user creation process
        print(f"Error creating student profile: {str(e)}")

    
class Program(models.Model):
    PROGRAM_TYPES = (
        ('PRE_KOREA', 'Pre-Korea'),
        ('K_LIP', 'K-Lip'),
        ('EXAM', 'Exam Registration'),
    )
    
    name = models.CharField(max_length=100)
    program_type = models.CharField(max_length=20, choices=PROGRAM_TYPES)
    description = models.TextField()
    brochure = models.FileField(
        upload_to='brochures/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.brochure:
            encrypt_file(self.brochure.path)
        super().save(*args, **kwargs)

    def get_brochure(self):
        if self.brochure:
            return decrypt_file(self.brochure.path)
        return None
    
    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date")

    def __str__(self):
        return self.name

class ProgramApplication(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    application_date = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_applications'
    )
    review_date = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    application_document = models.FileField(
        upload_to='program_applications/',
        null=True,  # Allow null for existing records
        blank=True, # Allow blank in forms
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    
class Activity(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='activities/')
    published_date = models.DateTimeField(auto_now_add=True)
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_date']
        verbose_name_plural = 'Activities'

    def __str__(self):
        return self.title
    
class ContactInquiry(models.Model):
    INQUIRY_TYPES = (
        ('general', 'General Inquiry'),
        ('program', 'Program Information'),
        ('admission', 'Admission Query'),
        ('support', 'Technical Support'),
        ('other', 'Other')
    )
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    inquiry_type = models.CharField(
        max_length=20, 
        choices=INQUIRY_TYPES, 
        default='general'
    )
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    response = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    responded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='contact_responses'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Inquiry'
        verbose_name_plural = 'Contact Inquiries'

    def __str__(self):
        return f"{self.name} - {self.subject}"

    def mark_as_read(self, user):
        """Mark the inquiry as read"""
        if not self.is_read:
            self.is_read = True
            self.save()

    def add_response(self, user, response_text):
        """Add a response to the inquiry"""
        self.response = response_text
        self.responded_by = user
        self.responded_at = timezone.now()
        self.save()

    @property
    def is_responded(self):
        """Check if the inquiry has been responded to"""
        return bool(self.response)

    @property
    def response_time(self):
        """Calculate response time in hours"""
        if self.responded_at:
            time_diff = self.responded_at - self.created_at
            return round(time_diff.total_seconds() / 3600, 1)
        return None