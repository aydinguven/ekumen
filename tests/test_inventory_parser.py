"""
Tests for Ekumen Inventory Parser service.
"""

from ekumen.services.inventory_parser import parse_inventory


def test_parse_simple_ini_inventory():
    """Test parsing simple flat INI inventory."""
    content = "192.168.1.10\n192.168.1.11\nweb.example.com"
    data = parse_inventory(content)

    assert data['total_hosts'] == 3
    assert '192.168.1.10' in data['all_hosts']
    assert 'web.example.com' in data['all_hosts']


def test_parse_grouped_ini_inventory():
    """Test parsing grouped INI inventory with host vars and group vars."""
    content = """
    [webservers]
    web1.example.com http_port=80 maxClients=200
    web2.example.com http_port=80

    [dbservers]
    db1.example.com

    [webservers:vars]
    ntp_server = pool.ntp.org

    [production:children]
    webservers
    dbservers
    """
    data = parse_inventory(content)

    assert data['total_hosts'] == 3
    assert 'webservers' in data['groups']
    assert 'dbservers' in data['groups']
    assert 'production' in data['groups']

    web_hosts = [h['name'] for h in data['groups']['webservers']['hosts']]
    assert 'web1.example.com' in web_hosts
    assert data['groups']['webservers']['vars'].get('ntp_server') == 'pool.ntp.org'
    assert 'webservers' in data['groups']['production']['children']


def test_parse_yaml_inventory():
    """Test parsing YAML inventory."""
    content = """---
all:
  children:
    webservers:
      hosts:
        web1:
          ansible_host: 192.168.1.50
        web2:
      vars:
        domain: example.com
"""
    data = parse_inventory(content)
    assert data['total_hosts'] == 2
    assert 'web1' in data['all_hosts']
    assert 'web2' in data['all_hosts']
    assert 'webservers' in data['groups']
    assert data['groups']['webservers']['vars'].get('domain') == 'example.com'


def test_parse_empty_inventory():
    """Test parsing empty or comment-only inventory."""
    assert parse_inventory("").get('total_hosts') == 0
    assert parse_inventory("# comment only").get('total_hosts') == 0
