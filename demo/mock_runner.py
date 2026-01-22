"""
Ekumen - Mock Runner Module (DEMO)
Simulates execution of Ansible ad-hoc commands and playbooks for demo purposes.
"""

import time
import random
import datetime

class MockRunner:
    def __init__(self):
        self.ansible_available = True
    
    def run(self, data):
        """Simulate running an Ansible command."""
        mode = data.get('mode', 'adhoc')
        inventory_content = data.get('inventory', '')
        verbosity = data.get('verbosity', '')
        
        # Simulate network latency
        time.sleep(random.uniform(0.5, 2.0))
        
        # Parse hosts from inventory (simple simulation)
        hosts = [line.strip() for line in inventory_content.split('\n') 
                 if line.strip() and not line.strip().startswith(('#', '['))]
        
        if not hosts:
            hosts = ["10.0.0.51", "10.0.0.52", "10.0.0.53"]
            
        output_buffer = []
        success = True
        
        # Add verbosity header if requested
        if verbosity:
            output_buffer.append(f"Using /etc/ansible/ansible.cfg as config file")
            output_buffer.append(f"SSH password: ")
            output_buffer.append(f"BECOME password[defaults to SSH password]: ")
            output_buffer.append("")

        if mode == 'adhoc':
            module = data.get('module', 'ping')
            args = data.get('args', '')
            
            for host in hosts:
                # Simulate a failure for a specific host or randomly
                if "fail" in host or (random.random() < 0.1 and len(hosts) > 1):
                    output_buffer.append(f"{host} | FAILED! => {{")
                    output_buffer.append(f'    "msg": "Authentication failed or connection timed out",')
                    output_buffer.append(f'    "changed": false')
                    output_buffer.append(f"}}")
                else:
                    output_buffer.append(f"{host} | SUCCESS => {{")
                    output_buffer.append(f'    "ansible_facts": {{')
                    output_buffer.append(f'        "discovered_interpreter_python": "/usr/bin/python3"')
                    output_buffer.append(f'    }},')
                    output_buffer.append(f'    "changed": false,')
                    output_buffer.append(f'    "ping": "pong"')
                    if module == "command" or module == "shell":
                         output_buffer.append(f'    ,"stdout": "Simulated output for: {args}",')
                         output_buffer.append(f'    "rc": 0')
                    output_buffer.append(f"}}")
                    
        else: # playbook
            output_buffer.append(f"PLAY [Setup Web Server and Serve System Info] **************************************************")
            output_buffer.append("")
            
            output_buffer.append(f"TASK [Gathering Facts] *************************************************************************")
            for host in hosts:
                output_buffer.append(f"ok: [{host}]")
            output_buffer.append("")

            tasks = ["Install Apache", "Start Service", "Deploy Content"]
            for task in tasks:
                 output_buffer.append(f"TASK [{task}] *************************************************************************")
                 for host in hosts:
                    if random.random() < 0.2:
                        output_buffer.append(f"changed: [{host}]")
                    else:
                        output_buffer.append(f"ok: [{host}]")
                 output_buffer.append("")
            
            output_buffer.append(f"PLAY RECAP *************************************************************************************")
            for host in hosts:
                output_buffer.append(f"{host.ljust(26)} : ok=4    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   ")

        return {
            'success': success,
            'output': "\n".join(output_buffer),
            'error': ''
        }
