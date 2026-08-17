"""
Tests for Ekumen Collection Manager service.
"""

import os
import json
import pytest
from ekumen.services.collections import CollectionManager


def test_validate_collection_name():
    """Test validation of FQCN collection names."""
    mgr = CollectionManager('/tmp/c', '/tmp/r')

    assert mgr.validate_collection_name('community.general') == 'community.general'
    assert mgr.validate_collection_name('ansible.posix:1.5.0') == 'ansible.posix:1.5.0'
    assert mgr.validate_collection_name('my_org.my_collection:>=2.0.0') == 'my_org.my_collection:>=2.0.0'

    with pytest.raises(ValueError):
        mgr.validate_collection_name('invalid name with spaces')

    with pytest.raises(ValueError):
        mgr.validate_collection_name('../traversal')


def test_validate_role_name():
    """Test validation of role names."""
    mgr = CollectionManager('/tmp/c', '/tmp/r')

    assert mgr.validate_role_name('geerlingguy.docker') == 'geerlingguy.docker'
    assert mgr.validate_role_name('common') == 'common'

    with pytest.raises(ValueError):
        mgr.validate_role_name('bad/name')


def test_collection_discovery(temp_dirs):
    """Test discovering installed collections and reading manifests."""
    mgr = CollectionManager(
        collections_path=temp_dirs['collections_path'],
        roles_path=temp_dirs['roles_path']
    )

    # Mock collection filesystem layout
    # ansible_collections/test_ns/test_col/MANIFEST.json
    col_path = os.path.join(temp_dirs['collections_path'], 'ansible_collections', 'test_ns', 'test_col')
    modules_dir = os.path.join(col_path, 'plugins', 'modules')
    os.makedirs(modules_dir, exist_ok=True)

    manifest_data = {
        'collection_info': {
            'namespace': 'test_ns',
            'name': 'test_col',
            'version': '1.2.3'
        }
    }
    with open(os.path.join(col_path, 'MANIFEST.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f)

    # Create dummy module file
    with open(os.path.join(modules_dir, 'custom_mod.py'), 'w', encoding='utf-8') as f:
        f.write("# module")

    collections = mgr.list_collections()
    assert len(collections) == 1
    col = collections[0]
    assert col.fqcn == 'test_ns.test_col'
    assert col.version == '1.2.3'
    assert 'custom_mod' in col.modules

    # Test get_collection
    single_col = mgr.get_collection('test_ns.test_col')
    assert single_col is not None
    assert single_col.version == '1.2.3'

    # Non-existent
    assert mgr.get_collection('non.existent') is None


def test_requirements_export_and_import(temp_dirs):
    """Test exporting and importing requirements.yml."""
    mgr = CollectionManager(
        collections_path=temp_dirs['collections_path'],
        roles_path=temp_dirs['roles_path']
    )

    # Export empty
    req_yaml = mgr.export_requirements_yaml()
    assert '---' in req_yaml

    # Import empty or invalid
    res = mgr.import_requirements_yaml("")
    assert res['success'] is False

    invalid_yaml = mgr.import_requirements_yaml("invalid: [yaml: {")
    assert invalid_yaml['success'] is False
