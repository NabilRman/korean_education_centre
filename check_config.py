# korean_education_centre/check_config.py
import sys
import os
from pathlib import Path

def check_configuration():
    print("Current working directory:", os.getcwd())
    print("\nPython path:")
    for path in sys.path:
        print(f"  - {path}")
    
    print("\nChecking key files:")
    files_to_check = [
        'manage.py',
        'kec/settings.py',
        'kec/wsgi.py',
        'kec/__init__.py'
    ]
    
    for file in files_to_check:
        path = Path(file)
        print(f"  - {file}: {'EXISTS' if path.is_file() else 'MISSING'}")

if __name__ == '__main__':
    check_configuration()