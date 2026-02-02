
import time
import random

class MockAnsibleRunner:
    def __init__(self, allowed_modules=None):
        # Always return True for the demo
        self.ansible_available = True
    
    def run(self, data):
        """
        Simulate Ansible execution with mocked data.
        """
        # Simulate network/processing delay to make it feel real
        time.sleep(random.uniform(0.5, 2.0))
        
        mode = data.get('mode', 'adhoc')
        inventory = data.get('inventory', '')
        
        # Check for error triggering in inventory for demo purposes
        if "error" in inventory.lower() or "fail" in inventory.lower():
             return {
                'success': False,
                'output': "",
                'error': "FAILED! => {\n    \"msg\": \"Failed to connect to the host via ssh: ssh: connect to host 192.168.1.100 port 22: Connection refused\"\n}"
            }

        if mode == 'adhoc':
            module = data.get('module', 'ping')
            args = data.get('args', '')
            
            output = self._get_mock_adhoc_output(module, args)
            return {
                'success': True,
                'output': output,
                'error': ''
            }
        else:
            # Playbook mode
            playbook_content = data.get('playbook', '')
            output = self._get_mock_playbook_output(playbook_content)
            return {
                'success': True,
                'output': output,
                'error': ''
            }

    def _get_mock_adhoc_output(self, module, args):
        host = "192.168.1.10"
        
        if module == 'ping':
            return f"""{host} | SUCCESS => {{
    "ansible_facts": {{
        "discovered_interpreter_python": "/usr/bin/python3"
    }},
    "changed": false,
    "ping": "pong"
}}"""
        elif module == 'command' or module == 'shell':
            if 'uptime' in args:
                return f"{host} | CHANGED | rc=0 >>\n 14:32:01 up 45 days, 2:12,  1 user,  load average: 0.01, 0.04, 0.05"
            elif 'free' in args:
                return f"""{host} | CHANGED | rc=0 >>
              total        used        free      shared  buff/cache   available
Mem:        8174856     1234568     5432100       12345     1508188     6654321
Swap:       2097148           0     2097148"""
            elif 'ls' in args or 'dir' in args:
                return f"""{host} | CHANGED | rc=0 >>
anaconda-ks.cfg
original-ks.cfg
test_file.txt
var_log_copy.tar.gz"""
            else:
                 return f"{host} | CHANGED | rc=0 >>\nCommand '{module} {args}' executed successfully (Simulated Output)"
        
        elif module == 'setup':
             return f"""{host} | SUCCESS => {{
    "ansible_facts": {{
        "ansible_all_ipv4_addresses": [
            "192.168.1.10"
        ],
        "ansible_architecture": "x86_64",
        "ansible_distribution": "CentOS",
        "ansible_distribution_major_version": "8",
        "ansible_memtotal_mb": 7900,
        "ansible_os_family": "RedHat",
        "ansible_processor_vcpus": 2
    }},
    "changed": false
}}"""

        return f"{host} | SUCCESS => {{\n    \"changed\": true,\n    \"msg\": \"Simulated execution of {module}\"\n}}"

    def _get_mock_playbook_output(self, content):
        # Extract hosts if possible, otherwise default
        host = "192.168.1.10"
        
        return f"""
PLAY [Simulated Deployment] ****************************************************

TASK [Gathering Facts] *********************************************************
ok: [{host}]

TASK [Install required packages] ***********************************************
changed: [{host}] => (item=nginx)
ok: [{host}] => (item=postgresql)

TASK [Ensure service is running] **********************************************
changed: [{host}]

TASK [Copy configuration file] *************************************************
changed: [{host}]

TASK [Restart service] *********************************************************
changed: [{host}]

PLAY RECAP *********************************************************************
{host}             : ok=5    changed=4    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   
"""
