# korean_education_centre/django_ssl.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

ssl_cert = str(BASE_DIR / 'ssl' / 'certificate.crt')
ssl_key = str(BASE_DIR / 'ssl' / 'private.key')

DJANGO_EXTENSIONS_SETTINGS = {
    'runserver_plus': {
        'ssl_certificate': ssl_cert,
        'ssl_key': ssl_key,
    },
}