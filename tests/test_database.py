"""
Tests for Ekumen JobDatabase SQLite service.
"""

import os
from ekumen.services.database import JobDatabase


def test_job_database_lifecycle(temp_dirs):
    """Test full CRUD lifecycle of JobDatabase."""
    db_path = os.path.join(temp_dirs['base'], 'test_jobs.db')
    db = JobDatabase(db_path=db_path)

    job_data = {
        'id': 'test_job_1',
        'mode': 'playbook',
        'target_name': 'deploy.yml',
        'status': 'running',
        'start_time': '2026-08-17T12:00:00',
        'host_count': 3,
        'hosts_summary': 'host1, host2, host3',
        'params': {
            'playbook': '--- ...',
            'password': 'secret_password_123',
            'become_password': 'secret_become_456'
        }
    }

    job_id = db.create_job(job_data)
    assert job_id == 'test_job_1'

    # Get job
    job = db.get_job('test_job_1')
    assert job is not None
    assert job['status'] == 'running'
    assert job['target_name'] == 'deploy.yml'
    # Verify passwords were not stored in params
    assert 'password' not in job['params']
    assert 'become_password' not in job['params']

    # Update job
    db.update_job('test_job_1', {
        'status': 'success',
        'duration': 4.2,
        'recap_ok': 5,
        'recap_changed': 2,
        'output': 'PLAY RECAP\nhost1 : ok=5 changed=2 unreachable=0 failed=0'
    })

    updated_job = db.get_job('test_job_1')
    assert updated_job['status'] == 'success'
    assert updated_job['duration'] == 4.2
    assert updated_job['recap_ok'] == 5
    assert updated_job['recap_changed'] == 2

    # List jobs
    jobs = db.list_jobs(limit=10)
    assert len(jobs) == 1
    assert jobs[0]['id'] == 'test_job_1'

    # Delete job
    assert db.delete_job('test_job_1') is True
    assert db.get_job('test_job_1') is None

    # Clear jobs
    db.create_job(job_data)
    assert len(db.list_jobs()) == 1
    assert db.clear_jobs() is True
    assert len(db.list_jobs()) == 0
