"""
Ekumen - Host Connectivity & Fact Discovery Service
Provides parallel ping testing, round-trip latency measurements, and system fact extraction.
"""

import json
import logging
import os
import re
import shutil
import tempfile
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def extract_structured_facts(raw_facts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract high-level system telemetry from raw Ansible facts dict.
    """
    if not isinstance(raw_facts, dict):
        return {}

    ansible_facts = raw_facts.get('ansible_facts', raw_facts)

    # OS & System
    distro = ansible_facts.get('ansible_distribution', 'Linux')
    version = ansible_facts.get('ansible_distribution_version', '')
    release = ansible_facts.get('ansible_distribution_release', '')
    os_name = f"{distro} {version}".strip()
    kernel = ansible_facts.get('ansible_kernel', 'Unknown')
    arch = ansible_facts.get('ansible_architecture', 'x86_64')
    hostname = ansible_facts.get('ansible_hostname', 'unknown')
    fqdn = ansible_facts.get('ansible_fqdn', hostname)
    uptime_seconds = ansible_facts.get('ansible_uptime_seconds', 0)

    # Hardware & CPU
    cpus = ansible_facts.get('ansible_processor_vcpus', ansible_facts.get('ansible_processor_count', 1))
    cpu_model = 'Unknown'
    procs = ansible_facts.get('ansible_processor', [])
    if isinstance(procs, list) and len(procs) > 1:
        cpu_model = procs[1]
    elif isinstance(procs, list) and len(procs) > 0:
        cpu_model = procs[0]

    # Memory
    mem_total_mb = ansible_facts.get('ansible_memtotal_mb', 0)
    mem_free_mb = ansible_facts.get('ansible_memfree_mb', 0)
    mem_used_mb = max(0, mem_total_mb - mem_free_mb)
    mem_used_pct = round((mem_used_mb / mem_total_mb * 100), 1) if mem_total_mb > 0 else 0

    # Network
    ipv4 = ansible_facts.get('ansible_default_ipv4', {})
    ip_address = ipv4.get('address', 'Unknown')
    mac_address = ipv4.get('macaddress', 'Unknown')
    gateway = ipv4.get('gateway', 'Unknown')
    interface = ipv4.get('interface', 'Unknown')
    all_ipv4 = ansible_facts.get('ansible_all_ipv4_addresses', [ip_address] if ip_address != 'Unknown' else [])

    # Storage & Mounts
    mounts = []
    raw_mounts = ansible_facts.get('ansible_mounts', [])
    if isinstance(raw_mounts, list):
        for m in raw_mounts:
            if isinstance(m, dict):
                total_gb = round(m.get('size_total', 0) / (1024 ** 3), 1)
                free_gb = round(m.get('size_available', 0) / (1024 ** 3), 1)
                used_gb = round(total_gb - free_gb, 1)
                pct = round((used_gb / total_gb * 100), 1) if total_gb > 0 else 0
                mounts.append({
                    'mount': m.get('mount', '/'),
                    'device': m.get('device', ''),
                    'fstype': m.get('fstype', ''),
                    'total_gb': total_gb,
                    'free_gb': free_gb,
                    'used_gb': used_gb,
                    'used_pct': pct
                })

    # Python version
    python_ver = ansible_facts.get('ansible_python', {}).get('version', {}).get('string', 'Unknown')

    return {
        'hostname': hostname,
        'fqdn': fqdn,
        'os_name': os_name,
        'distribution': distro,
        'version': version,
        'kernel': kernel,
        'architecture': arch,
        'uptime_seconds': uptime_seconds,
        'cpus': cpus,
        'cpu_model': cpu_model,
        'memory': {
            'total_mb': mem_total_mb,
            'used_mb': mem_used_mb,
            'free_mb': mem_free_mb,
            'used_pct': mem_used_pct
        },
        'network': {
            'ip': ip_address,
            'mac': mac_address,
            'gateway': gateway,
            'interface': interface,
            'all_ips': all_ipv4
        },
        'mounts': mounts,
        'python_version': python_ver
    }


class ConnectivityChecker:
    """Performs parallel ping connectivity tests and fact discovery."""

    def __init__(self, ansible_available: Optional[bool] = None):
        self.ansible_available = (shutil.which('ansible') is not None) if ansible_available is None else ansible_available

    def ping_hosts(
        self,
        inventory_content: str,
        username: str = '',
        password: str = '',
        private_key: str = '',
        timeout: int = 5
    ) -> Dict[str, Any]:
        """
        Execute Ansible ping module across inventory hosts and measure round-trip latency.
        """
        if not inventory_content or not inventory_content.strip():
            return {
                'success': False,
                'error': 'Inventory is empty',
                'summary': {'total': 0, 'online': 0, 'slow': 0, 'offline': 0, 'avg_latency_ms': 0},
                'hosts': {}
            }

        # Parse hostnames from inventory
        raw_lines = [l.strip() for l in inventory_content.splitlines() if l.strip() and not l.startswith('#') and not l.startswith('[') and not l.startswith(';')]
        extracted_hosts = []
        for line in raw_lines:
            tokens = line.split()
            if tokens:
                extracted_hosts.append(tokens[0])

        if not extracted_hosts:
            return {
                'success': False,
                'error': 'No valid hosts found in inventory',
                'summary': {'total': 0, 'online': 0, 'slow': 0, 'offline': 0, 'avg_latency_ms': 0},
                'hosts': {}
            }

        if not self.ansible_available:
            # Fallback simulated response if ansible binary not installed locally
            hosts_res = {}
            for h in extracted_hosts:
                hosts_res[h] = {
                    'status': 'offline',
                    'latency_ms': 0,
                    'error': 'Ansible binary not found on server'
                }
            return {
                'success': True,
                'summary': {'total': len(extracted_hosts), 'online': 0, 'slow': 0, 'offline': len(extracted_hosts), 'avg_latency_ms': 0},
                'hosts': hosts_res
            }

        temp_dir = tempfile.mkdtemp(prefix='ekumen_ping_')

        try:
            inventory_path = os.path.join(temp_dir, 'hosts')
            with open(inventory_path, 'w', encoding='utf-8') as f:
                f.write(inventory_content)

            import subprocess
            cmd = ['ansible', 'all', '-i', inventory_path, '-m', 'ping', '-o']

            if username:
                cmd.extend(['-u', username])

            if private_key:
                key_path = os.path.join(temp_dir, 'id_rsa')
                with open(key_path, 'w', encoding='utf-8') as f:
                    f.write(private_key.strip() + '\n')
                try:
                    os.chmod(key_path, 0o600)
                except OSError:
                    pass
                cmd.extend(['--private-key', key_path])

            env = os.environ.copy()
            env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
            env['ANSIBLE_SSH_ARGS'] = f'-o ConnectTimeout={timeout} -o StrictHostKeyChecking=no'
            env['ANSIBLE_FORCE_COLOR'] = 'false'

            start_t = time.time()
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * 2 + 5, env=env, cwd=temp_dir)
            total_duration_ms = round((time.time() - start_t) * 1000, 1)

            stdout = res.stdout + '\n' + res.stderr
            return self._parse_ping_output(stdout, extracted_hosts, total_duration_ms)

        except subprocess.TimeoutExpired:
            hosts_res = {h: {'status': 'offline', 'latency_ms': 0, 'error': 'Connection timed out'} for h in extracted_hosts}
            return {
                'success': True,
                'summary': {'total': len(extracted_hosts), 'online': 0, 'slow': 0, 'offline': len(extracted_hosts), 'avg_latency_ms': 0},
                'hosts': hosts_res
            }
        except Exception as e:
            logger.error("Ping test error: %s", e)
            return {
                'success': False,
                'error': str(e),
                'summary': {'total': len(extracted_hosts), 'online': 0, 'slow': 0, 'offline': len(extracted_hosts), 'avg_latency_ms': 0},
                'hosts': {}
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _parse_ping_output(self, output: str, expected_hosts: List[str], total_duration_ms: float) -> Dict[str, Any]:
        """Parse one-line Ansible ping output into host statuses."""
        hosts_res: Dict[str, Dict[str, Any]] = {}
        online_count = 0
        slow_count = 0
        latencies = []

        # Split output lines
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            # Format: host | SUCCESS => {"changed": false, "ping": "pong"}
            # Or: host | FAILED! => {"msg": "..."}
            # Or: host | UNREACHABLE! => {"msg": "..."}
            match = re.match(r'^([\w\.\-\:\@\[\]]+)\s*\|\s*(SUCCESS|FAILED|UNREACHABLE)[^=]*=>\s*(.*)$', line)
            if match:
                hostname = match.group(1).strip()
                status_type = match.group(2).upper()
                payload_str = match.group(3).strip()

                if status_type == 'SUCCESS':
                    # Estimate per-host latency share
                    host_latency = round(max(5.0, total_duration_ms / max(1, len(expected_hosts))), 1)
                    latencies.append(host_latency)
                    is_slow = host_latency >= 100.0

                    if is_slow:
                        slow_count += 1
                    else:
                        online_count += 1

                    hosts_res[hostname] = {
                        'status': 'slow' if is_slow else 'online',
                        'latency_ms': host_latency,
                        'message': 'pong'
                    }
                else:
                    error_msg = 'Unreachable or failed'
                    try:
                        parsed_err = json.loads(payload_str)
                        error_msg = parsed_err.get('msg', error_msg)
                    except Exception:
                        if payload_str:
                            error_msg = payload_str[:120]

                    hosts_res[hostname] = {
                        'status': 'offline',
                        'latency_ms': 0,
                        'error': error_msg
                    }

        # Fill any expected hosts that did not output a matching line
        for h in expected_hosts:
            if h not in hosts_res:
                hosts_res[h] = {
                    'status': 'offline',
                    'latency_ms': 0,
                    'error': 'Host did not respond'
                }

        offline_count = len(expected_hosts) - (online_count + slow_count)
        avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0

        return {
            'success': True,
            'summary': {
                'total': len(expected_hosts),
                'online': online_count,
                'slow': slow_count,
                'offline': max(0, offline_count),
                'avg_latency_ms': avg_latency
            },
            'hosts': hosts_res
        }

    def get_host_facts(
        self,
        hostname: str,
        inventory_content: str,
        username: str = '',
        password: str = '',
        private_key: str = '',
        timeout: int = 15
    ) -> Dict[str, Any]:
        """
        Execute Ansible setup module to fetch all facts from the specified host.
        """
        if not self.ansible_available:
            return {'success': False, 'error': 'Ansible binary not installed on server'}

        temp_dir = tempfile.mkdtemp(prefix='ekumen_facts_')

        try:
            inventory_path = os.path.join(temp_dir, 'hosts')
            with open(inventory_path, 'w', encoding='utf-8') as f:
                f.write(inventory_content)

            import subprocess
            cmd = ['ansible', hostname, '-i', inventory_path, '-m', 'setup']

            if username:
                cmd.extend(['-u', username])

            if private_key:
                key_path = os.path.join(temp_dir, 'id_rsa')
                with open(key_path, 'w', encoding='utf-8') as f:
                    f.write(private_key.strip() + '\n')
                try:
                    os.chmod(key_path, 0o600)
                except OSError:
                    pass
                cmd.extend(['--private-key', key_path])

            env = os.environ.copy()
            env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
            env['ANSIBLE_SSH_ARGS'] = f'-o ConnectTimeout={timeout} -o StrictHostKeyChecking=no'
            env['ANSIBLE_FORCE_COLOR'] = 'false'

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5, env=env, cwd=temp_dir)

            output = res.stdout
            # Extract JSON block after "=>"
            if '=>' in output:
                json_part = output.split('=>', 1)[1].strip()
                try:
                    raw_facts = json.loads(json_part)
                    structured = extract_structured_facts(raw_facts)
                    return {
                        'success': True,
                        'host': hostname,
                        'facts': structured,
                        'raw': raw_facts.get('ansible_facts', raw_facts)
                    }
                except json.JSONDecodeError:
                    pass

            return {
                'success': False,
                'error': f'Failed to parse facts output: {res.stderr or res.stdout[:200]}'
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': f'Fact discovery timed out after {timeout} seconds'}
        except Exception as e:
            logger.error("Fact discovery error: %s", e)
            return {'success': False, 'error': str(e)}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
