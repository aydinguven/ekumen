"""
Tests for Ekumen Ansible Runner service.
"""

from ekumen.services.runner import AnsibleRunner, DEFAULT_SAFE_MODULES


def test_runner_initialization():
    """Test AnsibleRunner initialization and module restrictions."""
    runner = AnsibleRunner(allowed_modules=['ping', 'setup'])
    assert 'ping' in runner.allowed_modules
    assert 'setup' in runner.allowed_modules
    assert 'yum' not in runner.allowed_modules

    # Default fallback
    default_runner = AnsibleRunner()
    assert 'ping' in default_runner.allowed_modules
    assert 'command' in default_runner.allowed_modules


def test_validate_inventory():
    """Test inventory validation."""
    runner = AnsibleRunner()

    valid, err = runner.validate_inventory("192.168.1.1\nweb2.domain.com")
    assert valid is True

    valid, err = runner.validate_inventory("")
    assert valid is False
    assert "required" in err.lower()

    valid, err = runner.validate_inventory("# only comments\n# here")
    assert valid is False


def test_validate_module():
    """Test module safety checks."""
    runner = AnsibleRunner(allowed_modules=['ping', 'setup'])

    valid, _ = runner.validate_module('ping')
    assert valid is True

    valid, err = runner.validate_module('unauthorized_module')
    assert valid is False
    assert "not in the allowed modules" in err


def test_run_ansible_unavailable():
    """Test runner behavior when ansible is not available."""
    runner = AnsibleRunner()
    runner.ansible_available = False

    res = runner.run({'mode': 'adhoc', 'inventory': 'localhost', 'module': 'ping'})
    assert res['success'] is False
    assert 'not installed' in res['error'].lower()
