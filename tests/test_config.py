"""
Tests for Ekumen configuration and environment variable loading.
"""

import os
from unittest import mock
from ekumen.config import Config, _get_env, _get_env_bool, _get_env_int


def test_default_config():
    """Test default configuration values."""
    assert Config.VERSION is not None
    assert isinstance(Config.HOST, str)
    assert isinstance(Config.PORT, int)
    assert isinstance(Config.COMMAND_TIMEOUT, int)
    assert isinstance(Config.SSH_CONNECT_TIMEOUT, int)


def test_env_helpers_primary_and_legacy():
    """Test environment variable resolution with primary and legacy fallbacks."""
    # Test primary priority
    with mock.patch.dict(os.environ, {'EKUMEN_HOST': '127.0.0.1', 'ANSIBLE_SHUTTLE_HOST': '192.168.1.1'}):
        assert _get_env('EKUMEN_HOST', 'ANSIBLE_SHUTTLE_HOST', '0.0.0.0') == '127.0.0.1'

    # Test legacy fallback when primary is unset
    with mock.patch.dict(os.environ, {'ANSIBLE_SHUTTLE_HOST': '192.168.1.1'}, clear=True):
        assert _get_env('EKUMEN_HOST', 'ANSIBLE_SHUTTLE_HOST', '0.0.0.0') == '192.168.1.1'

    # Test default when both unset
    with mock.patch.dict(os.environ, {}, clear=True):
        assert _get_env('EKUMEN_HOST', 'ANSIBLE_SHUTTLE_HOST', '0.0.0.0') == '0.0.0.0'


def test_env_bool_and_int_helpers():
    """Test boolean and integer parsing."""
    with mock.patch.dict(os.environ, {'EKUMEN_DEBUG': 'true', 'EKUMEN_PORT': '8080'}):
        assert _get_env_bool('EKUMEN_DEBUG', default=False) is True
        assert _get_env_int('EKUMEN_PORT', default=5000) == 8080

    with mock.patch.dict(os.environ, {'EKUMEN_DEBUG': '0', 'EKUMEN_PORT': 'invalid'}):
        assert _get_env_bool('EKUMEN_DEBUG', default=True) is False
        assert _get_env_int('EKUMEN_PORT', default=5000) == 5000


def test_config_to_dict():
    """Test Config.to_dict() export."""
    d = Config.to_dict()
    assert 'VERSION' in d
    assert 'HOST' in d
    assert 'PORT' in d
    assert 'PLAYBOOK_DIR' in d
    assert 'INVENTORY_DIR' in d
