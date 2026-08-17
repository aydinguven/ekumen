"""
Tests for Ekumen Host Connectivity and Fact Discovery services.
"""

from ekumen.services.connectivity import ConnectivityChecker, extract_structured_facts


def test_extract_structured_facts():
    """Test parsing structured facts from raw Ansible setup dictionary."""
    raw_facts = {
        'ansible_facts': {
            'ansible_distribution': 'Ubuntu',
            'ansible_distribution_version': '22.04',
            'ansible_kernel': '5.15.0-generic',
            'ansible_architecture': 'x86_64',
            'ansible_hostname': 'node-ubuntu',
            'ansible_processor_vcpus': 4,
            'ansible_processor': ['x86_64', 'Intel(R) Xeon(R) CPU @ 2.80GHz'],
            'ansible_memtotal_mb': 8192,
            'ansible_memfree_mb': 4096,
            'ansible_default_ipv4': {
                'address': '192.168.1.100',
                'macaddress': '52:54:00:12:34:56',
                'interface': 'eth0',
                'gateway': '192.168.1.1'
            },
            'ansible_mounts': [
                {
                    'mount': '/',
                    'device': '/dev/sda1',
                    'fstype': 'ext4',
                    'size_total': 100 * (1024 ** 3),
                    'size_available': 60 * (1024 ** 3)
                }
            ]
        }
    }

    facts = extract_structured_facts(raw_facts)

    assert facts['distribution'] == 'Ubuntu'
    assert facts['os_name'] == 'Ubuntu 22.04'
    assert facts['kernel'] == '5.15.0-generic'
    assert facts['cpus'] == 4
    assert facts['memory']['total_mb'] == 8192
    assert facts['memory']['used_mb'] == 4096
    assert facts['memory']['used_pct'] == 50.0
    assert facts['network']['ip'] == '192.168.1.100'
    assert facts['network']['mac'] == '52:54:00:12:34:56'
    assert len(facts['mounts']) == 1
    assert facts['mounts'][0]['mount'] == '/'
    assert facts['mounts'][0]['total_gb'] == 100.0


def test_extract_facts_empty():
    """Test extract_structured_facts handles empty/corrupt dict gracefully."""
    facts = extract_structured_facts({})
    assert facts.get('distribution') == 'Linux'
    assert facts['memory']['total_mb'] == 0


def test_parse_ping_output():
    """Test parsing one-line ping output into structured latency metrics."""
    checker = ConnectivityChecker(ansible_available=True)
    sample_output = """
    192.168.1.10 | SUCCESS => {"ansible_facts": {"discovered_interpreter_python": "/usr/bin/python3"}, "changed": false, "ping": "pong"}
    192.168.1.11 | UNREACHABLE! => {"changed": false, "msg": "Failed to connect to the host via ssh: Permission denied", "unreachable": true}
    """

    res = checker._parse_ping_output(sample_output, ['192.168.1.10', '192.168.1.11'], total_duration_ms=45.0)

    assert res['success'] is True
    assert res['summary']['total'] == 2
    assert res['summary']['online'] == 1
    assert res['summary']['offline'] == 1
    assert res['hosts']['192.168.1.10']['status'] == 'online'
    assert res['hosts']['192.168.1.11']['status'] == 'offline'
    assert 'Permission denied' in res['hosts']['192.168.1.11']['error']


def test_connectivity_api_endpoints(client):
    """Test /connectivity/ping and /connectivity/facts endpoints."""
    # Test ping with empty inventory
    res_empty = client.post('/connectivity/ping', json={})
    assert res_empty.status_code == 400

    # Test ping with inventory
    res_ping = client.post('/connectivity/ping', json={'inventory': '192.168.1.10'})
    assert res_ping.status_code == 200
    data = res_ping.get_json()
    assert 'summary' in data
    assert 'hosts' in data

    # Test facts without host
    res_no_host = client.post('/connectivity/facts', json={})
    assert res_no_host.status_code == 400
