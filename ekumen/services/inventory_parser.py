"""
Ekumen - Inventory Parser & Explorer Service
Parses INI and YAML inventories into structured host-group hierarchies.
"""

import re
from typing import Dict, Any, List
import yaml


def parse_inventory(content: str) -> Dict[str, Any]:
    """
    Parse INI or YAML inventory text into structured hierarchy.
    """
    if not content or not content.strip():
        return {
            'total_hosts': 0,
            'groups': {},
            'all_hosts': []
        }

    raw = content.strip()

    # Detect if YAML format
    if raw.startswith('---') or (raw.startswith('all:') or 'hosts:' in raw and ':' in raw.splitlines()[0]):
        try:
            parsed_yaml = yaml.safe_load(raw)
            if isinstance(parsed_yaml, dict):
                return _parse_yaml_inventory(parsed_yaml)
        except Exception:
            pass

    return _parse_ini_inventory(raw)


def _parse_ini_inventory(content: str) -> Dict[str, Any]:
    """Parse INI format inventory."""
    groups: Dict[str, Dict[str, Any]] = {
        'ungrouped': {'hosts': [], 'vars': {}, 'children': []}
    }
    all_hosts = set()
    current_group = 'ungrouped'
    mode = 'hosts'  # 'hosts', 'vars', 'children'

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.startswith(';'):
            continue

        # Check for group header: [group_name], [group:vars], [group:children]
        group_match = re.match(r'^\[([\w\.\-]+)(?::(vars|children))?\]$', line)
        if group_match:
            group_name = group_match.group(1)
            group_type = group_match.group(2) or 'hosts'

            if group_name not in groups:
                groups[group_name] = {'hosts': [], 'vars': {}, 'children': []}

            current_group = group_name
            mode = group_type
            continue

        if mode == 'hosts':
            # Extract hostname/IP (first token) and any host variables
            tokens = line.split()
            hostname = tokens[0]
            host_vars = {}
            for token in tokens[1:]:
                if '=' in token:
                    k, v = token.split('=', 1)
                    host_vars[k] = v

            if current_group not in groups:
                groups[current_group] = {'hosts': [], 'vars': {}, 'children': []}

            groups[current_group]['hosts'].append({
                'name': hostname,
                'vars': host_vars
            })
            all_hosts.add(hostname)

        elif mode == 'vars':
            if '=' in line:
                k, v = line.split('=', 1)
                groups[current_group]['vars'][k.strip()] = v.strip()
            elif ':' in line:
                k, v = line.split(':', 1)
                groups[current_group]['vars'][k.strip()] = v.strip()

        elif mode == 'children':
            child_group = line.split()[0]
            groups[current_group]['children'].append(child_group)

    # Clean up empty ungrouped if other groups exist
    if len(groups['ungrouped']['hosts']) == 0 and len(groups) > 1:
        del groups['ungrouped']

    return {
        'total_hosts': len(all_hosts),
        'all_hosts': sorted(list(all_hosts)),
        'groups': groups
    }


def _parse_yaml_inventory(data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse YAML format inventory dictionary."""
    groups: Dict[str, Dict[str, Any]] = {}
    all_hosts = set()

    def process_group(name: str, gdata: Dict[str, Any]):
        if not isinstance(gdata, dict):
            return

        if name not in groups:
            groups[name] = {'hosts': [], 'vars': {}, 'children': []}

        # Process hosts
        hosts = gdata.get('hosts', {})
        if isinstance(hosts, dict):
            for hname, hvars in hosts.items():
                groups[name]['hosts'].append({
                    'name': str(hname),
                    'vars': hvars if isinstance(hvars, dict) else {}
                })
                all_hosts.add(str(hname))
        elif isinstance(hosts, list):
            for hname in hosts:
                groups[name]['hosts'].append({'name': str(hname), 'vars': {}})
                all_hosts.add(str(hname))

        # Process vars
        gvars = gdata.get('vars', {})
        if isinstance(gvars, dict):
            groups[name]['vars'].update(gvars)

        # Process children
        children = gdata.get('children', {})
        if isinstance(children, dict):
            for cname, cdata in children.items():
                groups[name]['children'].append(cname)
                process_group(cname, cdata)

    if 'all' in data:
        process_group('all', data['all'])
    else:
        for gname, gdata in data.items():
            process_group(gname, gdata)

    return {
        'total_hosts': len(all_hosts),
        'all_hosts': sorted(list(all_hosts)),
        'groups': groups
    }
