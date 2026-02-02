"""
Ekumen - Collection Manager Module
Manages Ansible collections and roles via ansible-galaxy CLI.
"""

import os
import re
import json
import shutil
import subprocess
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple


@dataclass
class CollectionInfo:
    """Information about an installed Ansible collection."""
    namespace: str          # e.g., "community"
    name: str               # e.g., "general"
    fqcn: str               # e.g., "community.general"
    version: str            # e.g., "8.0.0"
    path: str               # filesystem path
    modules: List[str]      # list of module names

    def to_dict(self):
        return asdict(self)


@dataclass
class RoleInfo:
    """Information about an installed Ansible role."""
    name: str               # e.g., "geerlingguy.docker"
    version: str            # e.g., "7.0.0" or "unknown"
    path: str               # filesystem path

    def to_dict(self):
        return asdict(self)


class CollectionManager:
    """Manages Ansible collections and roles via ansible-galaxy CLI."""

    def __init__(self, collections_path: str = None, roles_path: str = None, timeout: int = 300):
        """
        Initialize the Collection Manager.
        
        Args:
            collections_path: Path to collections directory (default: /opt/ekumen/collections)
            roles_path: Path to roles directory (default: /opt/ekumen/roles)
            timeout: Timeout for galaxy operations in seconds (default: 300)
        """
        self.collections_path = collections_path or '/opt/ekumen/collections'
        self.roles_path = roles_path or '/opt/ekumen/roles'
        self.timeout = timeout
        self.galaxy_available = shutil.which('ansible-galaxy') is not None

    # ========== VALIDATION ==========

    def _validate_collection_name(self, name: str) -> str:
        """
        Validate and sanitize collection name.
        Allows: namespace.collection or namespace.collection:version
        """
        # Remove any whitespace
        name = name.strip()
        
        # Pattern for FQCN with optional version
        pattern = r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+(?::[a-zA-Z0-9\.\-\*>=<,]+)?$'
        if not re.match(pattern, name):
            raise ValueError(f"Invalid collection name: {name}")
        
        # Check for path traversal
        if '/' in name or '\\' in name or '..' in name:
            raise ValueError("Invalid characters in collection name")
        
        return name

    def _validate_role_name(self, name: str) -> str:
        """
        Validate and sanitize role name.
        Allows: namespace.rolename or just rolename
        """
        name = name.strip()
        
        # Pattern for role name with optional namespace
        pattern = r'^[a-zA-Z0-9_\-]+(?:\.[a-zA-Z0-9_\-]+)?$'
        if not re.match(pattern, name):
            raise ValueError(f"Invalid role name: {name}")
        
        # Check for path traversal
        if '/' in name or '\\' in name or '..' in name:
            raise ValueError("Invalid characters in role name")
        
        return name

    # ========== DISCOVERY ==========

    def _get_collections_base_path(self) -> str:
        """Get the ansible_collections subdirectory."""
        return os.path.join(self.collections_path, 'ansible_collections')

    def _get_collection_modules(self, collection_path: str) -> List[str]:
        """
        Enumerate modules within a collection.
        """
        modules_dir = os.path.join(collection_path, 'plugins', 'modules')
        if not os.path.exists(modules_dir):
            return []
        
        modules = []
        try:
            for f in os.listdir(modules_dir):
                if f.endswith('.py') and not f.startswith('_'):
                    modules.append(f.replace('.py', ''))
        except OSError:
            pass
        
        return sorted(modules)

    def _read_collection_manifest(self, collection_path: str) -> Dict:
        """Read the collection's MANIFEST.json for metadata."""
        manifest_path = os.path.join(collection_path, 'MANIFEST.json')
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _read_galaxy_yml(self, collection_path: str) -> Dict:
        """Read galaxy.yml as fallback for version info."""
        galaxy_path = os.path.join(collection_path, 'galaxy.yml')
        if os.path.exists(galaxy_path):
            try:
                import yaml
                with open(galaxy_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        return {}

    def list_collections(self) -> List[CollectionInfo]:
        """
        List all installed collections.
        
        Returns:
            List of CollectionInfo objects
        """
        collections = []
        base_path = self._get_collections_base_path()
        
        if not os.path.exists(base_path):
            return collections
        
        try:
            # Iterate through namespaces
            for namespace in os.listdir(base_path):
                namespace_path = os.path.join(base_path, namespace)
                if not os.path.isdir(namespace_path):
                    continue
                
                # Iterate through collections in namespace
                for collection_name in os.listdir(namespace_path):
                    collection_path = os.path.join(namespace_path, collection_name)
                    if not os.path.isdir(collection_path):
                        continue
                    
                    # Get version from MANIFEST.json or galaxy.yml
                    manifest = self._read_collection_manifest(collection_path)
                    version = "unknown"
                    
                    if manifest and 'collection_info' in manifest:
                        version = manifest['collection_info'].get('version', 'unknown')
                    else:
                        galaxy_yml = self._read_galaxy_yml(collection_path)
                        version = galaxy_yml.get('version', 'unknown')
                    
                    # Get modules
                    modules = self._get_collection_modules(collection_path)
                    
                    collections.append(CollectionInfo(
                        namespace=namespace,
                        name=collection_name,
                        fqcn=f"{namespace}.{collection_name}",
                        version=version,
                        path=collection_path,
                        modules=modules
                    ))
        except OSError as e:
            print(f"Error listing collections: {e}")
        
        # Sort by FQCN
        collections.sort(key=lambda c: c.fqcn)
        return collections

    def list_roles(self) -> List[RoleInfo]:
        """
        List all installed roles.
        
        Returns:
            List of RoleInfo objects
        """
        roles = []
        
        if not os.path.exists(self.roles_path):
            return roles
        
        try:
            for role_name in os.listdir(self.roles_path):
                role_path = os.path.join(self.roles_path, role_name)
                if not os.path.isdir(role_path):
                    continue
                
                # Skip hidden directories
                if role_name.startswith('.'):
                    continue
                
                # Try to get version from meta/main.yml
                version = "unknown"
                meta_path = os.path.join(role_path, 'meta', 'main.yml')
                if os.path.exists(meta_path):
                    try:
                        import yaml
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = yaml.safe_load(f) or {}
                            if 'galaxy_info' in meta:
                                version = meta['galaxy_info'].get('version', 'unknown')
                    except Exception:
                        pass
                
                roles.append(RoleInfo(
                    name=role_name,
                    version=version,
                    path=role_path
                ))
        except OSError as e:
            print(f"Error listing roles: {e}")
        
        # Sort by name
        roles.sort(key=lambda r: r.name)
        return roles

    def get_collection(self, fqcn: str) -> Optional[CollectionInfo]:
        """
        Get details for a specific collection.
        
        Args:
            fqcn: Fully Qualified Collection Name (e.g., "community.general")
            
        Returns:
            CollectionInfo or None if not found
        """
        collections = self.list_collections()
        for c in collections:
            if c.fqcn == fqcn:
                return c
        return None

    def get_role(self, name: str) -> Optional[RoleInfo]:
        """
        Get details for a specific role.
        
        Args:
            name: Role name
            
        Returns:
            RoleInfo or None if not found
        """
        roles = self.list_roles()
        for r in roles:
            if r.name == name:
                return r
        return None

    # ========== INSTALLATION ==========

    def _run_galaxy_command(self, args: List[str]) -> Tuple[bool, str, str]:
        """
        Run an ansible-galaxy command.
        
        Args:
            args: Command arguments (after 'ansible-galaxy')
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        if not self.galaxy_available:
            return False, "", "ansible-galaxy is not installed or not in PATH"
        
        cmd = ['ansible-galaxy'] + args
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**os.environ, 'ANSIBLE_FORCE_COLOR': 'false'}
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {self.timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    def install_collection(self, name: str, version: str = None, force: bool = False) -> Dict:
        """
        Install a collection from Ansible Galaxy.
        
        Args:
            name: Collection FQCN (e.g., "community.general")
            version: Optional version (e.g., "8.0.0")
            force: Force reinstall if already installed
            
        Returns:
            Dict with success, output, error keys
        """
        try:
            # Validate and sanitize
            name = self._validate_collection_name(name)
        except ValueError as e:
            return {'success': False, 'output': '', 'error': str(e)}
        
        # Build install target
        target = name
        if version:
            target = f"{name}:{version}"
        
        # Build command
        args = ['collection', 'install', target, '-p', self.collections_path]
        if force:
            args.append('--force')
        
        success, stdout, stderr = self._run_galaxy_command(args)
        
        return {
            'success': success,
            'output': stdout,
            'error': stderr if not success else ''
        }

    def install_role(self, name: str, version: str = None, force: bool = False) -> Dict:
        """
        Install a role from Ansible Galaxy.
        
        Args:
            name: Role name (e.g., "geerlingguy.docker")
            version: Optional version
            force: Force reinstall if already installed
            
        Returns:
            Dict with success, output, error keys
        """
        try:
            name = self._validate_role_name(name)
        except ValueError as e:
            return {'success': False, 'output': '', 'error': str(e)}
        
        # Build install target
        target = name
        if version:
            target = f"{name},{version}"
        
        # Build command
        args = ['role', 'install', target, '-p', self.roles_path]
        if force:
            args.append('--force')
        
        success, stdout, stderr = self._run_galaxy_command(args)
        
        return {
            'success': success,
            'output': stdout,
            'error': stderr if not success else ''
        }

    # ========== DELETION ==========

    def delete_collection(self, fqcn: str) -> Dict:
        """
        Delete an installed collection.
        
        Args:
            fqcn: Fully Qualified Collection Name
            
        Returns:
            Dict with success and error keys
        """
        collection = self.get_collection(fqcn)
        if not collection:
            return {'success': False, 'error': f"Collection '{fqcn}' not found"}
        
        try:
            shutil.rmtree(collection.path)
            
            # Clean up empty namespace directory
            namespace_path = os.path.dirname(collection.path)
            if os.path.exists(namespace_path) and not os.listdir(namespace_path):
                os.rmdir(namespace_path)
            
            return {'success': True, 'error': ''}
        except OSError as e:
            return {'success': False, 'error': str(e)}

    def delete_role(self, name: str) -> Dict:
        """
        Delete an installed role.
        
        Args:
            name: Role name
            
        Returns:
            Dict with success and error keys
        """
        role = self.get_role(name)
        if not role:
            return {'success': False, 'error': f"Role '{name}' not found"}
        
        try:
            shutil.rmtree(role.path)
            return {'success': True, 'error': ''}
        except OSError as e:
            return {'success': False, 'error': str(e)}

    # ========== REQUIREMENTS EXPORT ==========

    def export_requirements_yaml(self) -> str:
        """
        Export installed collections and roles as requirements.yml content.
        
        Returns:
            YAML string
        """
        collections = self.list_collections()
        roles = self.list_roles()
        
        lines = ['---']
        
        if collections:
            lines.append('collections:')
            for c in collections:
                if c.version and c.version != 'unknown':
                    lines.append(f'  - name: {c.fqcn}')
                    lines.append(f'    version: "{c.version}"')
                else:
                    lines.append(f'  - name: {c.fqcn}')
        
        if roles:
            lines.append('')
            lines.append('roles:')
            for r in roles:
                if r.version and r.version != 'unknown':
                    lines.append(f'  - name: {r.name}')
                    lines.append(f'    version: "{r.version}"')
                else:
                    lines.append(f'  - name: {r.name}')
        
        return '\n'.join(lines)

    def import_requirements_yaml(self, content: str, force: bool = False) -> Dict:
        """
        Import and install collections and roles from requirements.yml content.
        
        Args:
            content: YAML string with collections and roles to install
            force: Force reinstall if already installed
            
        Returns:
            Dict with results for each item
        """
        try:
            import yaml
            data = yaml.safe_load(content)
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to parse YAML: {str(e)}',
                'results': []
            }
        
        if not data:
            return {
                'success': False,
                'error': 'Empty requirements file',
                'results': []
            }
        
        results = []
        all_success = True
        
        # Process collections
        collections = data.get('collections', [])
        for item in collections:
            if isinstance(item, str):
                name = item
                version = None
            elif isinstance(item, dict):
                name = item.get('name', item.get('src', ''))
                version = item.get('version')
            else:
                continue
            
            if not name:
                continue
                
            result = self.install_collection(name, version, force)
            results.append({
                'type': 'collection',
                'name': name,
                'version': version,
                'success': result['success'],
                'error': result.get('error', '')
            })
            if not result['success']:
                all_success = False
        
        # Process roles
        roles = data.get('roles', [])
        for item in roles:
            if isinstance(item, str):
                name = item
                version = None
            elif isinstance(item, dict):
                name = item.get('name', item.get('src', ''))
                version = item.get('version')
            else:
                continue
            
            if not name:
                continue
                
            result = self.install_role(name, version, force)
            results.append({
                'type': 'role',
                'name': name,
                'version': version,
                'success': result['success'],
                'error': result.get('error', '')
            })
            if not result['success']:
                all_success = False
        
        return {
            'success': all_success,
            'error': '' if all_success else 'Some items failed to install',
            'results': results
        }

