# korean_education_centre/core/utils.py
from cryptography.fernet import Fernet
import os
from django.conf import settings
import base64

def get_encryption_key():
    """
    Retrieve or generate an encryption key for file operations.
    The key should be stored in Django settings or environment variables in production.
    """
    # In production, this should come from environment variables
    key = getattr(settings, 'FILE_ENCRYPTION_KEY', None)
    if not key:
        # Generate a key if not exists
        key = base64.urlsafe_b64encode(Fernet.generate_key())
        # In production, save this key securely
    return key

def encrypt_file(file_path):
    """
    Encrypt a file using Fernet symmetric encryption.
    
    Args:
        file_path (str): Path to the file to be encrypted
    """
    if not os.path.exists(file_path):
        return
        
    key = get_encryption_key()
    f = Fernet(key)
    
    # Read the file content
    with open(file_path, 'rb') as file:
        file_data = file.read()
    
    # Encrypt the data
    encrypted_data = f.encrypt(file_data)
    
    # Write the encrypted data back
    with open(file_path, 'wb') as file:
        file.write(encrypted_data)

def decrypt_file(file_path):
    """
    Decrypt a file using Fernet symmetric encryption.
    
    Args:
        file_path (str): Path to the encrypted file
        
    Returns:
        bytes: Decrypted file content
    """
    if not os.path.exists(file_path):
        return None
        
    key = get_encryption_key()
    f = Fernet(key)
    
    # Read the encrypted file
    with open(file_path, 'rb') as file:
        encrypted_data = file.read()
    
    # Decrypt the data
    decrypted_data = f.decrypt(encrypted_data)
    
    return decrypted_data