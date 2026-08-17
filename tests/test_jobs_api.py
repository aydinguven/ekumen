"""
Tests for Ekumen Jobs, SSE streaming, Templates, and Inventory Parse APIs.
"""


def test_templates_api(client):
    """Test /templates endpoints."""
    res = client.get('/templates')
    assert res.status_code == 200
    templates = res.get_json()['templates']
    assert len(templates) >= 5

    # Get single template
    t_id = templates[0]['id']
    res_single = client.get(f'/templates/{t_id}')
    assert res_single.status_code == 200
    assert 'content' in res_single.get_json()['template']

    # Non existent template
    res_404 = client.get('/templates/nonexistent')
    assert res_404.status_code == 404


def test_inventory_parse_api(client):
    """Test /inventories/parse endpoint."""
    content = "[web]\n192.168.1.50 http_port=80"
    res = client.post('/inventories/parse', json={'content': content})
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['data']['total_hosts'] == 1
    assert 'web' in data['data']['groups']


def test_jobs_api_lifecycle(client):
    """Test asynchronous jobs API endpoints and history."""
    # Invalid payload
    res_bad = client.post('/jobs', json={})
    assert res_bad.status_code == 400

    # Start valid async job
    payload = {
        'mode': 'adhoc',
        'module': 'ping',
        'inventory': 'localhost',
        'username': 'ansible_user'
    }
    res_start = client.post('/jobs', json=payload)
    assert res_start.status_code == 200
    data = res_start.get_json()
    assert data['success'] is True
    job_id = data['job_id']
    assert data['stream_url'] == f'/jobs/{job_id}/stream'

    # Check SSE stream response headers
    res_stream = client.get(f'/jobs/{job_id}/stream')
    assert res_stream.status_code == 200
    assert 'text/event-stream' in res_stream.headers['Content-Type']

    # List jobs
    res_list = client.get('/jobs')
    assert res_list.status_code == 200
    jobs = res_list.get_json()['jobs']
    assert any(j['id'] == job_id for j in jobs)

    # Get specific job
    res_get = client.get(f'/jobs/{job_id}')
    assert res_get.status_code == 200
    assert res_get.get_json()['job']['id'] == job_id

    # Cancel job
    client.post(f'/jobs/{job_id}/cancel')

    # Delete job
    res_del = client.delete(f'/jobs/{job_id}')
    assert res_del.status_code == 200
    assert res_del.get_json()['success'] is True

    # Clear all jobs
    res_clear = client.delete('/jobs')
    assert res_clear.status_code == 200
    assert res_clear.get_json()['success'] is True
