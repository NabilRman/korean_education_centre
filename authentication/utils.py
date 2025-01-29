# korean_education_centre/authentication/ utils.py
import random
from django.core.cache import cache
from django.conf import settings
from twilio.rest import Client
from .models import SystemLog
import logging 
import pyotp

logger = logging.getLogger(__name__)

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return str(random.randint(100000, 999999))

def store_verification_code(user_id, code, expire_minutes=10):
    """Store verification code in cache"""
    cache_key = f'phone_verification_{user_id}'
    cache.set(cache_key, code, timeout=expire_minutes * 60)

def verify_phone_code(user, code):
    """Verify the phone verification code"""
    cache_key = f'phone_verification_{user.id}'
    stored_code = cache.get(cache_key)
    if stored_code and stored_code == code:
        cache.delete(cache_key)
        return True
    return False

def send_sms_console(phone_number, message):
    """Development backend that prints SMS to console"""
    print(f"\nSMS to {phone_number}:")
    print(f"Message: {message}")
    logger.info(f"SMS sent (console) to {phone_number}: {message}")
    return True

def send_sms_twilio(phone_number, message):
    """Production backend that sends real SMS via Twilio"""
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        twilio_message = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        logger.info(f"SMS sent (Twilio) to {phone_number}: {twilio_message.sid}")
        return True
    except ImportError:
        logger.error("Twilio package not installed")
        return False
    except Exception as e:
        logger.error(f"Error sending SMS via Twilio: {str(e)}")
        return False

def send_phone_verification(user, phone_number):
    """Send verification code via configured SMS backend"""
    code = generate_verification_code()
    store_verification_code(user.id, code)
    
    # Store the pending phone number
    profile = user.userprofile
    profile.pending_phone_number = phone_number
    profile.save()

    message = f'Your KEC verification code is: {code}'
    
    # Use appropriate backend based on settings
    if settings.SMS_BACKEND == 'twilio':
        success = send_sms_twilio(phone_number, message)
    else:  # 'console' backend
        success = send_sms_console(phone_number, message)
    
    if not success:
        logger.error(f"Failed to send verification SMS to {phone_number}")
    
    return success

def log_system_event(request, category, action, severity='info', details=None):
    """
    Creates a system log entry to track important events.
    
    Args:
        request: The HTTP request object
        category: Type of event (login, security, profile, application, admin)
        action: Description of what happened
        severity: How important/serious the event is (info, warning, error, critical)
        details: Additional information as a dictionary
    """
    details = details or {}

    ip_address = None
    user_agent = ''
    if request:
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
    SystemLog.objects.create(
        category=category,
        user=request.user if request.user.is_authenticated else None,
        action=action,
        ip_address=request.META.get('REMOTE_ADDR'),
        severity=severity,
        user_agent=user_agent,
        details=details or {}
    )