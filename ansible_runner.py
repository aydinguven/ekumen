"""
Ekumen - Runner Module
Handles execution of Ansible ad-hoc commands and playbooks using pexpect
to manage interactive password prompts.
"""

import os
import re
import shutil
import pexpect
import shlex
import tempfile

# Safe modules allowed by default (can be overridden via config)
SAFE_MODULES = [
    'ping', 'command', 'shell', 'yum', 'dnf', 'apt', 'service', 'systemd',
    'copy', 'file', 'user', 'group', 'package', 'lineinfile', 'template',
    'debug', 'setup', 'raw', 'get_url', 'uri', 'stat', 'find', 'fetch',
    'hostname', 'cron', 'mount', 'sysctl', 'firewalld', 'iptables'
]

class AnsibleRunner:
    def __init__(self, allowed_modules=None):
        self.ansible_available = shutil.which('ansible') is not None
        self.allowed_modules = allowed_modules if allowed_modules else SAFE_MODULES
    
    def _validate_inventory(self, inventory_content):
        """Validate inventory content for basic safety."""
        if not inventory_content:
            return False, 'Inventory is required. Please provide at least one host.'
        
        # Check for basic patterns (hostnames, IPs)
        lines = inventory_content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('['):
                continue
            # Simple validation: alphanumeric, dots, dashes, underscores
            if not re.match(r'^[\w\.\-\:\@\[\]]+$', line.split()[0]):
                return False, f'Invalid host format: {line}'
        
        return True, ''
    
    def _validate_module(self, module):
        """Validate module name against allowed list."""
        if not module:
            return False, 'Module name is required.'
        
        if self.allowed_modules and module not in self.allowed_modules:
            return False, f'Module "{module}" is not allowed. Allowed modules: {", ".join(self.allowed_modules[:10])}...'
        
        return True, ''

    def _run_with_pexpect(self, cmd, password, become_password=None, timeout=120, cwd=None, env=None):
        """
        Run a command using pexpect to handle SSH and sudo password prompts.
        Returns (success, output, error)
        """
        try:
            # properly quote command for pexpect
            cmd_str = ' '.join(shlex.quote(arg) for arg in cmd)
            
            # Spawn the process with a proper PTY
            child = pexpect.spawn('/bin/bash', ['-c', cmd_str], timeout=timeout, cwd=cwd, env=env, encoding='utf-8')
            
            output_buffer = []
            ssh_password_sent = False
            become_password_sent = False
            
            # Patterns to match - order matters!
            patterns = [
                r'SSH password:',                    # 0: Ansible SSH password prompt
                r'BECOME password',                  # 1: Ansible become password prompt  
                r'(?i)password:',                    # 2: Generic password prompt
                r'(?i)yes/no',                       # 3: Host key confirmation (yes/no)
                r'\(yes/no/\[fingerprint\]\)',       # 4: Alternative host key prompt
                r'Are you sure you want to continue', # 5: Another host key prompt variant
                pexpect.EOF,                         # 6: End of output
                pexpect.TIMEOUT                      # 7: Timeout
            ]
            
            max_iterations = 30
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                try:
                    index = child.expect(patterns, timeout=20)
                    
                    # Capture any output before the match
                    if child.before:
                        output_buffer.append(child.before)
                    
                    if index == 0:  # SSH password prompt
                        child.sendline(password)
                        ssh_password_sent = True
                    elif index == 1:  # BECOME password prompt
                        pwd_to_send = become_password if become_password else password
                        child.sendline(pwd_to_send)
                        become_password_sent = True
                    elif index == 2:  # Generic password prompt
                        # Determine which password to send based on what we've already sent
                        if not ssh_password_sent:
                            child.sendline(password)
                            ssh_password_sent = True
                        elif not become_password_sent:
                            pwd_to_send = become_password if become_password else password
                            child.sendline(pwd_to_send)
                            become_password_sent = True
                        else:
                            # Already sent both, might be retrying
                            child.sendline(password)
                    elif index in [3, 4, 5]:  # Host key confirmation
                        child.sendline('yes')
                    elif index == 6:  # EOF - command finished
                        break
                    elif index == 7:  # Timeout
                        # Check if process is still alive
                        if not child.isalive():
                            break
                        continue
                        
                except pexpect.TIMEOUT:
                    if not child.isalive():
                        break
                    continue
                except pexpect.EOF:
                    break
            
            # Wait for process to complete
            child.close()
            
            # Get any remaining output
            full_output = ''.join(str(x) for x in output_buffer if x)
            
            # Get exit status
            success = child.exitstatus == 0 if child.exitstatus is not None else False
            
            return success, full_output, ''
            
        except pexpect.TIMEOUT:
            return False, '', 'Command timed out'
        except pexpect.EOF:
            return False, '', 'Unexpected end of output'
        except Exception as e:
            return False, '', str(e)

    def run(self, data):
        if not self.ansible_available:
            return {
                'success': False,
                'output': '',
                'error': 'Ansible is not installed or not in PATH. Please install Ansible to use this application.'
            }

        mode = data.get('mode', 'adhoc')
        inventory_content = data.get('inventory', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validate inventory
        valid, error = self._validate_inventory(inventory_content)
        if not valid:
            return {'success': False, 'output': '', 'error': error}

        temp_dir = tempfile.mkdtemp(prefix='ansible_runner_')
        
        try:
            # Create inventory file
            inventory_path = os.path.join(temp_dir, 'inventory')
            with open(inventory_path, 'w') as f:
                f.write(inventory_content)
            
            env = os.environ.copy()
            
            if mode == 'adhoc':
                module = data.get('module', 'ping')
                args = data.get('args', '').strip()
                
                cmd = [
                    'ansible',
                    'all',
                    '-i', inventory_path,
                    '-m', module
                ]
                
                if args:
                    cmd.extend(['-a', args])
                    
            else:  # playbook mode
                playbook_content = data.get('playbook', '').strip()
                
                if not playbook_content:
                    return {
                        'success': False,
                        'output': '',
                        'error': 'Playbook content is required.'
                    }
                
                playbook_path = os.path.join(temp_dir, 'playbook.yml')
                with open(playbook_path, 'w') as f:
                    f.write(playbook_content)
                
                cmd = [
                    'ansible-playbook',
                    '-i', inventory_path,
                    playbook_path
                ]
            
            # Authentication
            if username:
                cmd.extend(['-u', username])
            
            # Limit pattern (optional)
            limit = data.get('limit', '').strip()
            if limit:
                cmd.extend(['--limit', limit])
            
            # Privilege escalation
            become = data.get('become', True)
            become_method = data.get('become_method', 'sudo')
            become_user = data.get('become_user', 'root')
            become_password = data.get('become_password', password)
            
            if become:
                cmd.extend(['--become'])
                cmd.extend(['--become-method', become_method])
                cmd.extend(['--become-user', become_user])
            
            # Password flags
            if password:
                cmd.extend(['--ask-pass'])
            
            if become and become_password:
                cmd.extend(['--ask-become-pass'])
            
            # Environment setup
            env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
            # Fail faster on unreachable hosts
            env['ANSIBLE_SSH_ARGS'] = '-o ConnectTimeout=10 -o StrictHostKeyChecking=no'
            
            # Verbosity
            verbosity = data.get('verbosity', '')
            if verbosity in ['v', 'vv', 'vvv', 'vvvv']:
                cmd.append(f'-{verbosity}')
            
            # Execute
            success, output, error = self._run_with_pexpect(
                cmd, 
                password, 
                become_password=become_password,
                timeout=600, # 10 minutes timeout
                cwd=temp_dir, 
                env=env
            )
            
            return {
                'success': success,
                'output': output,
                'error': error
            }
            
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
