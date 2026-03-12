# ================= IMPORT =================

from cryptography.fernet import Fernet
import base64
import hashlib
import os


# ================= CREATE AES KEY =================

def generate_key(password):
    """
    Convert password into AES-256 key.
    """

    # Create 32-byte hash (AES-256 requires 32 bytes)
    key = hashlib.sha256(password.encode()).digest()

    # Convert into base64 format (required by Fernet)
    return base64.urlsafe_b64encode(key)


# ================= ENCRYPT FILE =================

def encrypt_file(input_path, output_path, password):

    key = generate_key(password)

    cipher = Fernet(key)

    # Read original file
    with open(input_path, "rb") as f:
        data = f.read()

    # Encrypt
    encrypted_data = cipher.encrypt(data)

    # Save encrypted file
    with open(output_path, "wb") as f:
        f.write(encrypted_data)


# ================= DECRYPT FILE =================

def decrypt_file(input_path, output_path, password):

    key = generate_key(password)

    cipher = Fernet(key)

    # Read encrypted file
    with open(input_path, "rb") as f:
        encrypted_data = f.read()

    # Decrypt
    decrypted_data = cipher.decrypt(encrypted_data)

    # Save decrypted file
    with open(output_path, "wb") as f:
        f.write(decrypted_data)
