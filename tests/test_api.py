"""
Tests for Ekumen Flask Blueprints and REST API endpoints.
"""

import json


def test_index_page(client):
    """Test loading the web interface."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Ekumen' in response.data


def test_runner_api_invalid_payload(client):
    """Test /run endpoint validation."""
    response = client.post('/run', json={})
    assert response.status_code == 400

    res = response.get_json()
    assert res['success'] is False


def test_runner_download_endpoint(client, app):
    """Test /download endpoint with and without output."""
    # When cache is empty
    res_empty = client.get('/download')
    assert res_empty.status_code == 404

    # Populate cache
    cache = app.extensions['ekumen']['output_cache']
    run_id = cache.store("Sample Ansible Output Log")

    # Download latest
    res_latest = client.get('/download')
    assert res_latest.status_code == 200
    assert b"Sample Ansible Output Log" in res_latest.data

    # Download by ID
    res_id = client.get(f'/download?id={run_id}')
    assert res_id.status_code == 200
    assert b"Sample Ansible Output Log" in res_id.data


def test_playbooks_api_crud(client):
    """Test full CRUD lifecycle of playbooks API."""
    # List initial
    res = client.get('/playbooks')
    assert res.status_code == 200
    assert res.get_json()['playbooks'] == []

    # Create playbook
    pb_payload = {
        'name': 'web_setup',
        'content': '---\n- name: Web\n  hosts: all\n'
    }
    res = client.post('/playbooks', json=pb_payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['name'] == 'web_setup.yml'

    # Get created playbook
    res = client.get('/playbooks/web_setup.yml')
    assert res.status_code == 200
    assert res.get_json()['content'] == pb_payload['content']

    # Get non-existent
    res = client.get('/playbooks/nonexistent.yml')
    assert res.status_code == 404

    # Delete playbook
    res = client.delete('/playbooks/web_setup.yml')
    assert res.status_code == 200
    assert res.get_json()['success'] is True

    # List again
    res = client.get('/playbooks')
    assert res.get_json()['playbooks'] == []


def test_inventories_api_crud(client):
    """Test full CRUD lifecycle of inventories API."""
    # List initial
    res = client.get('/inventories')
    assert res.status_code == 200
    assert res.get_json()['inventories'] == []

    # Create inventory
    inv_payload = {
        'name': 'staging',
        'content': '10.0.0.1\n10.0.0.2\n'
    }
    res = client.post('/inventories', json=inv_payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['name'] == 'staging.ini'

    # Get created inventory
    res = client.get('/inventories/staging.ini')
    assert res.status_code == 200
    assert res.get_json()['content'] == inv_payload['content']

    # Get non-existent
    res = client.get('/inventories/missing.ini')
    assert res.status_code == 404

    # Delete inventory
    res = client.delete('/inventories/staging.ini')
    assert res.status_code == 200
    assert res.get_json()['success'] is True

    # List again
    res = client.get('/inventories')
    assert res.get_json()['inventories'] == []


def test_collections_api(client):
    """Test collections, roles, and requirements endpoints."""
    res_col = client.get('/collections')
    assert res_col.status_code == 200
    assert 'collections' in res_col.get_json()

    res_roles = client.get('/roles')
    assert res_roles.status_code == 200
    assert 'roles' in res_roles.get_json()

    res_req = client.get('/requirements')
    assert res_req.status_code == 200
    assert b'---' in res_req.data

    # Test import with empty content
    res_import_bad = client.post('/requirements', json={})
    assert res_import_bad.status_code == 400
