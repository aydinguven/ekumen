"""
Ekumen - Runner Service
Handles execution of Ansible ad-hoc commands and playbooks using pexpect
to manage interactive password prompts and security controls.
"""

import logging
import os
import re
import shlex
import shutil
import tempfile
from typing import Dict, Any, Tuple, Optional, List

try:
    import pexpect
except ImportError:
    pexpect = None

logger = logging.getLogger(__name__)

# Safe modules allowed by default
DEFAULT_SAFE_MODULES = [
    'ping', 'command', 'shell', 'yum', 'dnf', 'apt', 'service', 'systemd',
    'copy', 'file', 'user', 'group', 'package', 'lineinfile', 'template',
    'debug', 'setup', 'raw', 'get_url', 'uri', 'stat', 'find', 'fetch',
    'hostname', 'cron', 'mount', 'sysctl', 'firewalld', 'iptables', 'git',
    'unarchive', 'archive', 'assert', 'fail', 'set_fact', 'pause', 'wait_for'
]


class AnsibleRunner:
    """Executes Ansible ad-hoc modules and playbooks securely."""

    def __init__(
        self,
        allowed_modules: Optional[List[str]] = None,
        collections_path: str = '/opt/ekumen/collections',
        roles_path: str = '/opt/ekumen/roles',
        command_timeout: int = 600,
        ssh_timeout: int = 10,
    ):
        self.ansible_available = (shutil.which('ansible') is not None and shutil.which('ansible-playbook') is not None)
        self.allowed_modules = allowed_modules if (allowed_modules and len(allowed_modules) > 0) else DEFAULT_SAFE_MODULES
        self.collections_path = collections_path
        self.roles_path = roles_path
        self.command_timeout = command_timeout
        self.ssh_timeout = ssh_timeout

    def validate_inventory(self, inventory_content: str) -> Tuple[bool, str]:
        """Validate inventory content for basic correctness and safety."""
        if not inventory_content or not inventory_content.strip():
            return False, 'Inventory is required. Please provide at least one host.'

        # Basic sanity checks: ensure at least one valid host entry or group
        has_content = False
        for line in inventory_content.splitlines():
            line = line.strip()
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            has_content = True
            break

        if not has_content:
            return False, 'Inventory cannot contain only comments or empty lines.'

        return True, ''

    def validate_module(self, module: str) -> Tuple[bool, str]:
        """Validate module name against allowed list."""
        if not module or not module.strip():
            return False, 'Module name is required.'

        mod = module.strip()
        # If allowed_modules is specified, check against it
        if self.allowed_modules and mod not in self.allowed_modules:
            preview = ", ".join(self.allowed_modules[:10])
            return False, f'Module "{mod}" is not in the allowed modules list ({preview}...)'

        return True, ''

    def _run_with_pexpect(
        self,
        cmd: List[str],
        password: str,
        become_password: Optional[str] = None,
        timeout: int = 600,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, str, str]:
        """
        Run a command using pexpect to handle SSH and sudo password prompts.
        Returns: (success, output, error)
        """
        if pexpect is None:
            return False, "", "pexpect module is not available on this platform"

        child = None
        try:
            cmd_str = ' '.join(shlex.quote(arg) for arg in cmd)

            # Spawn the process in a pseudo-terminal
            # Use /bin/bash or sh
            shell_exec = '/bin/bash' if os.path.exists('/bin/bash') else 'sh'
            child = pexpect.spawn(shell_exec, ['-c', cmd_str], timeout=timeout, cwd=cwd, env=env, encoding='utf-8')

            output_buffer = []
            ssh_password_sent = False
            become_password_sent = False

            # Match patterns
            patterns = [
                r'SSH password:',                      # 0: Ansible SSH password prompt
                r'BECOME password',                    # 1: Ansible become password prompt  
                r'(?i)password:',                      # 2: Generic password prompt
                r'(?i)yes/no',                         # 3: Host key confirmation (yes/no)
                r'\(yes/no/\[fingerprint\]\)',         # 4: Alternative host key prompt
                r'Are you sure you want to continue',   # 5: Another host key prompt variant
                pexpect.EOF,                           # 6: End of output
                pexpect.TIMEOUT                        # 7: Timeout
            ]

            max_iterations = 50
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                try:
                    index = child.expect(patterns, timeout=15)

                    if child.before:
                        output_buffer.append(child.before)

                    if index == 0:  # SSH password prompt
                        child.sendline(password)
                        ssh_password_sent = True
                    elif index == 1:  # BECOME password prompt
                        pwd = become_password if become_password else password
                        child.sendline(pwd)
                        become_password_sent = True
                    elif index == 2:  # Generic password prompt
                        if not ssh_password_sent:
                            child.sendline(password)
                            ssh_password_sent = True
                        elif not become_password_sent:
                            pwd = become_password if become_password else password
                            child.sendline(pwd)
                            become_password_sent = True
                        else:
                            child.sendline(password)
                    elif index in (3, 4, 5):  # Host key confirmation
                        child.sendline('yes')
                    elif index == 6:  # EOF
                        break
                    elif index == 7:  # Timeout check
                        if not child.isalive():
                            break
                        continue
                except pexpect.TIMEOUT:
                    if not child.isalive():
                        break
                    continue
                except pexpect.EOF:
                    break

            child.close()
            full_output = ''.join(str(x) for x in output_buffer if x)
            success = (child.exitstatus == 0) if child.exitstatus is not None else False
            return success, full_output, ''

        except pexpect.TIMEOUT:
            logger.warning("Ansible command timed out")
            if child and child.isalive():
                try:
                    child.close(force=True)
                except Exception:
                    pass
            return False, '', 'Command execution timed out'
        except pexpect.EOF:
            logger.warning("Unexpected EOF during execution")
            return False, '', 'Unexpected end of execution'
        except Exception as e:
            logger.error("Command execution failed: %s", e)
            if child and child.isalive():
                try:
                    child.close(force=True)
                except Exception:
                    pass
            return False, '', str(e)

    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Ansible ad-hoc command or playbook based on request payload.
        """
        if not self.ansible_available:
            logger.warning("Ansible binary not found")
            return {
                'success': False,
                'output': '',
                'error': 'Ansible is not installed or not in PATH. Please install Ansible on the server.'
            }

        mode = data.get('mode', 'adhoc')
        inventory_content = str(data.get('inventory', '')).strip()
        username = str(data.get('username', '')).strip()
        password = str(data.get('password', ''))

        # Validate inventory
        valid, inv_error = self.validate_inventory(inventory_content)
        if not valid:
            return {'success': False, 'output': '', 'error': inv_error}

        temp_dir = tempfile.mkdtemp(prefix='ekumen_run_')

        try:
            inventory_path = os.path.join(temp_dir, 'hosts')
            with open(inventory_path, 'w', encoding='utf-8') as f:
                f.write(inventory_content)

            env = os.environ.copy()

            if mode == 'adhoc':
                module = str(data.get('module', 'ping')).strip()
                valid_mod, mod_error = self.validate_module(module)
                if not valid_mod:
                    return {'success': False, 'output': '', 'error': mod_error}

                args = str(data.get('args', '')).strip()
                cmd = ['ansible', 'all', '-i', inventory_path, '-m', module]
                if args:
                    cmd.extend(['-a', args])

            else:  # playbook mode
                playbook_content = str(data.get('playbook', '')).strip()
                if not playbook_content:
                    return {
                        'success': False,
                        'output': '',
                        'error': 'Playbook content is required.'
                    }

                playbook_path = os.path.join(temp_dir, 'playbook.yml')
                with open(playbook_path, 'w', encoding='utf-8') as f:
                    f.write(playbook_content)

                cmd = ['ansible-playbook', '-i', inventory_path, playbook_path]

            # Options
            if username:
                cmd.extend(['-u', username])

            limit = str(data.get('limit', '')).strip()
            if limit:
                cmd.extend(['--limit', limit])

            # Privilege escalation
            become = bool(data.get('become', True))
            become_method = str(data.get('become_method', 'sudo')).strip()
            become_user = str(data.get('become_user', 'root')).strip()
            become_password = str(data.get('become_password', password))

            if become:
                cmd.extend(['--become'])
                if become_method:
                    cmd.extend(['--become-method', become_method])
                if become_user:
                    cmd.extend(['--become-user', become_user])

            if password:
                cmd.extend(['--ask-pass'])

            if become and become_password:
                cmd.extend(['--ask-become-pass'])

            # Verbosity
            verbosity = str(data.get('verbosity', '')).strip()
            if verbosity in ('v', 'vv', 'vvv', 'vvvv'):
                cmd.append(f'-{verbosity}')

            # Environment variables setup
            env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
            env['ANSIBLE_SSH_ARGS'] = f'-o ConnectTimeout={self.ssh_timeout} -o StrictHostKeyChecking=no'

            # Collection and Role Paths
            default_collections = '/root/.ansible/collections:/usr/share/ansible/collections'
            default_roles = '/root/.ansible/roles:/usr/share/ansible/roles:/etc/ansible/roles'
            env['ANSIBLE_COLLECTIONS_PATH'] = f'{self.collections_path}:{default_collections}'
            env['ANSIBLE_ROLES_PATH'] = f'{self.roles_path}:{default_roles}'

            success, output, error = self._run_with_pexpect(
                cmd=cmd,
                password=password,
                become_password=become_password,
                timeout=self.command_timeout,
                cwd=temp_dir,
                env=env
            )

            return {
                'success': success,
                'output': output,
                'error': error
            }

        except Exception as e:
            logger.error("Runner execution failed: %s", e)
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
