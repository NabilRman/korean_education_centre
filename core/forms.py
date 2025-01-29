#korean_education_centre/core/forms.py
from django import forms
from django.core.validators import FileExtensionValidator
from .models import ProgramApplication, Program, Activity, ContactInquiry

class ProgramApplicationForm(forms.ModelForm):
    application_document = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text='Please upload your application document in PDF format (max 5MB)'
    )

    class Meta:
        model = ProgramApplication
        fields = ['program', 'application_document']
        
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        self.fields['program'].queryset = Program.objects.filter(is_active=True)
    
    def clean_application_document(self):
        document = self.cleaned_data.get('application_document')
        if document:
            if document.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError('File size must be under 5MB.')
            if not document.name.endswith('.pdf'):
                raise forms.ValidationError('Only PDF files are allowed.')
        return document
    
    

    

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['title', 'content', 'image', 'is_active']
        
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError('Image file size must be under 5MB.')
        return image

class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ['name', 'program_type', 'description', 'brochure', 'start_date', 'end_date', 'is_active']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def clean_brochure(self):
        brochure = self.cleaned_data.get('brochure')
        if brochure:
            if brochure.size > 10 * 1024 * 1024:  # 10MB limit
                raise forms.ValidationError('Brochure file size must be under 10MB.')
            validator = FileExtensionValidator(allowed_extensions=['pdf'])
            validator(brochure)
        return brochure
    
class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactInquiry
        fields = ['name', 'email', 'phone', 'inquiry_type', 'subject', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 5}),
            'phone': forms.TextInput(attrs={'pattern': '[0-9+\-\s()]{10,15}'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove all non-numeric characters except +
            phone = ''.join(c for c in phone if c.isdigit() or c == '+')
            if not phone.startswith('+'):
                phone = '+' + phone
        return phone