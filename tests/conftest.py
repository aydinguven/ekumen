"""
Pytest configuration and test fixtures for Ekumen.
"""

import os
import tempfile
import pytest
from flask import Flask

from ekumen import create_app
from ekumen.config import Config


class TestConfig(Config):
    """Test configuration with isolated temp directories."""
    DEBUG = False
    SECRET_KEY = 'test-secret-key-123'
    COMMAND_TIMEOUT = 10
    SSH_CONNECT_TIMEOUT = 2
    ALLOWED_MODULES = ['ping', 'command', 'shell', 'debug']


@pytest.fixture
def temp_dirs():
    """Create isolated temporary directories for test storage."""
    base_dir = tempfile.mkdtemp(prefix='ekumen_test_')
    playbook_dir = os.path.join(base_dir, 'playbooks')
    inventory_dir = os.path.join(base_dir, 'inventories')
    collections_path = os.path.join(base_dir, 'collections')
    roles_path = os.path.join(base_dir, 'roles')
    cache_dir = os.path.join(base_dir, 'cache')

    for d in (playbook_dir, inventory_dir, collections_path, roles_path, cache_dir):
        os.makedirs(d, exist_ok=True)

    yield {
        'base': base_dir,
        'playbook_dir': playbook_dir,
        'inventory_dir': inventory_dir,
        'collections_path': collections_path,
        'roles_path': roles_path,
        'cache_dir': cache_dir,
    }

    import shutil
    shutil.rmtree(base_dir, ignore_errors=True)


@pytest.fixture
def app(temp_dirs):
    """Create a Flask application instance configured for testing."""
    class CustomConfig(TestConfig):
        PLAYBOOK_DIR = temp_dirs['playbook_dir']
        INVENTORY_DIR = temp_dirs['inventory_dir']
        COLLECTIONS_PATH = temp_dirs['collections_path']
        ROLES_PATH = temp_dirs['roles_path']
        OUTPUT_CACHE_DIR = temp_dirs['cache_dir']

    app = create_app(CustomConfig)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Test client fixture."""
    return app.test_client()
