"""
Ekumen Configuration
Centralized configuration with environment variable support.
"""

import os

class Config:
    """Application configuration loaded from environment variables."""
    
    VERSION = "1.3.0"
    
    # Flask settings
    DEBUG = os.environ.get('ANSIBLE_SHUTTLE_DEBUG', 'false').lower() == 'true'
    HOST = os.environ.get('ANSIBLE_SHUTTLE_HOST', '0.0.0.0')
    PORT = int(os.environ.get('ANSIBLE_SHUTTLE_PORT', 5000))
    
    # Security settings
    SECRET_KEY = os.environ.get('ANSIBLE_SHUTTLE_SECRET_KEY', os.urandom(24).hex())
    
    # Ansible settings
    COMMAND_TIMEOUT = int(os.environ.get('ANSIBLE_SHUTTLE_TIMEOUT', 600))
    SSH_CONNECT_TIMEOUT = int(os.environ.get('ANSIBLE_SHUTTLE_SSH_TIMEOUT', 10))
    
    # Allowed modules (empty list = all allowed)
    ALLOWED_MODULES = os.environ.get('ANSIBLE_SHUTTLE_ALLOWED_MODULES', '').split(',')
    ALLOWED_MODULES = [m.strip() for m in ALLOWED_MODULES if m.strip()]
