"""
Tests for Ekumen Playbook Manager service.
"""

import os
import pytest
from ekumen.services.playbooks import PlaybookManager


def test_playbook_manager_init(temp_dirs):
    """Test manager initialization and directory creation."""
    pb_dir = os.path.join(temp_dirs['base'], 'custom_pb')
    mgr = PlaybookManager(pb_dir)
    assert os.path.exists(pb_dir)
    assert mgr.list_playbooks() == []


def test_sanitize_name():
    """Test playbook name sanitization."""
    mgr = PlaybookManager('/tmp')

    assert mgr.sanitize_name('deploy') == 'deploy.yml'
    assert mgr.sanitize_name('deploy.yaml') == 'deploy.yaml'
    assert mgr.sanitize_name('deploy.yml') == 'deploy.yml'
    assert mgr.sanitize_name('evil/../../attack') == 'attack.yml'

    with pytest.raises(ValueError):
        mgr.sanitize_name('')


def test_playbook_crud_operations(temp_dirs):
    """Test saving, retrieving, listing, and deleting playbooks."""
    mgr = PlaybookManager(temp_dirs['playbook_dir'])

    content = "---\n- name: Test\n  hosts: all\n  tasks:\n    - ping:\n"
    success, saved_name = mgr.save_playbook('site', content)
    assert success is True
    assert saved_name == 'site.yml'

    # List playbooks
    playbooks = mgr.list_playbooks()
    assert 'site.yml' in playbooks

    # Get playbook
    success, retrieved_content = mgr.get_playbook('site.yml')
    assert success is True
    assert retrieved_content == content

    # Get non-existent
    success, err = mgr.get_playbook('nonexistent.yml')
    assert success is False
    assert 'not found' in err.lower()

    # Delete playbook
    success, err = mgr.delete_playbook('site.yml')
    assert success is True
    assert err is None
    assert mgr.list_playbooks() == []

    # Delete non-existent
    success, err = mgr.delete_playbook('site.yml')
    assert success is False
