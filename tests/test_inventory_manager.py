"""
Tests for Ekumen Inventory Manager service.
"""

import os
import pytest
from ekumen.services.inventories import InventoryManager


def test_inventory_manager_init(temp_dirs):
    """Test manager initialization and directory creation."""
    inv_dir = os.path.join(temp_dirs['base'], 'custom_inv')
    mgr = InventoryManager(inv_dir)
    assert os.path.exists(inv_dir)
    assert mgr.list_inventories() == []


def test_sanitize_name():
    """Test inventory name sanitization."""
    mgr = InventoryManager('/tmp')

    assert mgr.sanitize_name('webservers') == 'webservers.ini'
    assert mgr.sanitize_name('hosts.yaml') == 'hosts.yaml'
    assert mgr.sanitize_name('hosts.ini') == 'hosts.ini'
    assert mgr.sanitize_name('test/../attack') == 'attack.ini'

    with pytest.raises(ValueError):
        mgr.sanitize_name('')

    with pytest.raises(ValueError):
        mgr.sanitize_name('..')


def test_inventory_crud_operations(temp_dirs):
    """Test saving, retrieving, listing, and deleting inventories."""
    mgr = InventoryManager(temp_dirs['inventory_dir'])

    content = "192.168.1.10\n192.168.1.11\n\n[web]\nweb1.example.com"
    success, saved_name = mgr.save_inventory('production', content)
    assert success is True
    assert saved_name == 'production.ini'

    # List inventories
    inventories = mgr.list_inventories()
    assert 'production.ini' in inventories

    # Get inventory
    success, retrieved_content = mgr.get_inventory('production.ini')
    assert success is True
    assert retrieved_content == content

    # Get non-existent
    success, err = mgr.get_inventory('nonexistent.ini')
    assert success is False
    assert 'not found' in err.lower()

    # Delete inventory
    success, err = mgr.delete_inventory('production.ini')
    assert success is True
    assert err is None
    assert mgr.list_inventories() == []

    # Delete non-existent
    success, err = mgr.delete_inventory('production.ini')
    assert success is False
