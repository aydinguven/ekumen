"""
Ekumen - Configuration Module
Centralized configuration with environment variable support.
Supports EKUMEN_* primary variables and ANSIBLE_SHUTTLE_* legacy fallbacks.
"""

import os
import secrets


def _get_env(primary_key: str, legacy_key: str = None, default: str = "") -> str:
    """Retrieve environment variable checking primary key first, then legacy fallback."""
    val = os.environ.get(primary_key)
    if val is not None:
        return val
    if legacy_key:
        val = os.environ.get(legacy_key)
        if val is not None:
            return val
    return default


def _get_env_bool(primary_key: str, legacy_key: str = None, default: bool = False) -> bool:
    """Retrieve boolean from environment variable."""
    val = _get_env(primary_key, legacy_key, str(default)).strip().lower()
    return val in ('true', '1', 'yes', 'on')


def _get_env_int(primary_key: str, legacy_key: str = None, default: int = 0) -> int:
    """Retrieve integer from environment variable."""
    val = _get_env(primary_key, legacy_key, str(default)).strip()
    try:
        return int(val)
    except ValueError:
        return default


class Config:
    """Application configuration loaded from environment variables."""

    VERSION = "1.8.0"

    # Flask settings
    DEBUG = _get_env_bool('EKUMEN_DEBUG', 'ANSIBLE_SHUTTLE_DEBUG', default=False)
    HOST = _get_env('EKUMEN_HOST', 'ANSIBLE_SHUTTLE_HOST', default='0.0.0.0')
    PORT = _get_env_int('EKUMEN_PORT', 'ANSIBLE_SHUTTLE_PORT', default=5000)

    # Security settings
    SECRET_KEY = _get_env('EKUMEN_SECRET_KEY', 'ANSIBLE_SHUTTLE_SECRET_KEY', default=secrets.token_hex(24))

    # Ansible settings
    COMMAND_TIMEOUT = _get_env_int('EKUMEN_TIMEOUT', 'ANSIBLE_SHUTTLE_TIMEOUT', default=600)
    SSH_CONNECT_TIMEOUT = _get_env_int('EKUMEN_SSH_TIMEOUT', 'ANSIBLE_SHUTTLE_SSH_TIMEOUT', default=10)

    # Allowed modules (empty list = all safe default modules allowed)
    _raw_modules = _get_env('EKUMEN_ALLOWED_MODULES', 'ANSIBLE_SHUTTLE_ALLOWED_MODULES', default='')
    ALLOWED_MODULES = [m.strip() for m in _raw_modules.split(',') if m.strip()]

    # Storage Paths
    PLAYBOOK_DIR = _get_env('EKUMEN_PLAYBOOK_DIR', 'ANSIBLE_SHUTTLE_PLAYBOOK_DIR', default='/opt/ekumen/playbooks')
    INVENTORY_DIR = _get_env('EKUMEN_INVENTORY_DIR', 'ANSIBLE_SHUTTLE_INVENTORY_DIR', default='/opt/ekumen/inventories')
    COLLECTIONS_PATH = _get_env('EKUMEN_COLLECTIONS_PATH', default='/opt/ekumen/collections')
    ROLES_PATH = _get_env('EKUMEN_ROLES_PATH', default='/opt/ekumen/roles')

    # Galaxy settings
    GALAXY_TIMEOUT = _get_env_int('EKUMEN_GALAXY_TIMEOUT', default=300)

    # Output storage
    OUTPUT_CACHE_DIR = _get_env('EKUMEN_OUTPUT_CACHE_DIR', default='')

    @classmethod
    def to_dict(cls) -> dict:
        """Export config as dictionary for logging or debugging."""
        return {
            'VERSION': cls.VERSION,
            'DEBUG': cls.DEBUG,
            'HOST': cls.HOST,
            'PORT': cls.PORT,
            'COMMAND_TIMEOUT': cls.COMMAND_TIMEOUT,
            'SSH_CONNECT_TIMEOUT': cls.SSH_CONNECT_TIMEOUT,
            'ALLOWED_MODULES': cls.ALLOWED_MODULES,
            'PLAYBOOK_DIR': cls.PLAYBOOK_DIR,
            'INVENTORY_DIR': cls.INVENTORY_DIR,
            'COLLECTIONS_PATH': cls.COLLECTIONS_PATH,
            'ROLES_PATH': cls.ROLES_PATH,
            'GALAXY_TIMEOUT': cls.GALAXY_TIMEOUT,
        }
