"""
Ekumen - Collection Manager Service
Manages Ansible collections and roles via ansible-galaxy CLI and filesystem.
"""

import json
import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class CollectionInfo:
    """Information about an installed Ansible collection."""
    namespace: str
    name: str
    fqcn: str
    version: str
    path: str
    modules: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoleInfo:
    """Information about an installed Ansible role."""
    name: str
    version: str
    path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CollectionManager:
    """Manages Ansible collections and roles via ansible-galaxy CLI."""

    def __init__(self, collections_path: str = None, roles_path: str = None, timeout: int = 300):
        self.collections_path = os.path.abspath(collections_path or '/opt/ekumen/collections')
        self.roles_path = os.path.abspath(roles_path or '/opt/ekumen/roles')
        self.timeout = timeout
        self.galaxy_available = shutil.which('ansible-galaxy') is not None
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create collections and roles directories if missing."""
        for p in (self.collections_path, self.roles_path):
            if not os.path.exists(p):
                try:
                    os.makedirs(p, exist_ok=True)
                except OSError:
                    pass

    # ========== VALIDATION ==========

    def validate_collection_name(self, name: str) -> str:
        """
        Validate and sanitize collection name.
        Allows: namespace.collection or namespace.collection:version
        """
        name = name.strip()
        pattern = r'^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+(?::[a-zA-Z0-9\.\-\*>=<,]+)?$'
        if not re.match(pattern, name):
            raise ValueError(f"Invalid collection name: {name}")

        if '/' in name or '\\' in name or '..' in name:
            raise ValueError("Invalid characters in collection name")

        return name

    def validate_role_name(self, name: str) -> str:
        """
        Validate and sanitize role name.
        Allows: namespace.rolename or just rolename
        """
        name = name.strip()
        pattern = r'^[a-zA-Z0-9_\-]+(?:\.[a-zA-Z0-9_\-]+)?$'
        if not re.match(pattern, name):
            raise ValueError(f"Invalid role name: {name}")

        if '/' in name or '\\' in name or '..' in name:
            raise ValueError("Invalid characters in role name")

        return name

    # ========== DISCOVERY ==========

    def _get_collections_base_path(self) -> str:
        """Get the ansible_collections subdirectory."""
        return os.path.join(self.collections_path, 'ansible_collections')

    def _get_collection_modules(self, collection_path: str) -> List[str]:
        """Enumerate modules within a collection."""
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
                with open(galaxy_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        return {}

    def list_collections(self) -> List[CollectionInfo]:
        """List all installed collections."""
        collections = []
        base_path = self._get_collections_base_path()

        if not os.path.exists(base_path):
            return collections

        try:
            for namespace in os.listdir(base_path):
                namespace_path = os.path.join(base_path, namespace)
                if not os.path.isdir(namespace_path):
                    continue

                for collection_name in os.listdir(namespace_path):
                    collection_path = os.path.join(namespace_path, collection_name)
                    if not os.path.isdir(collection_path):
                        continue

                    manifest = self._read_collection_manifest(collection_path)
                    version = "unknown"

                    if manifest and 'collection_info' in manifest:
                        version = manifest['collection_info'].get('version', 'unknown')
                    else:
                        galaxy_yml = self._read_galaxy_yml(collection_path)
                        version = galaxy_yml.get('version', 'unknown')

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
            logger.error("Error listing collections: %s", e)

        collections.sort(key=lambda c: c.fqcn)
        return collections

    def list_roles(self) -> List[RoleInfo]:
        """List all installed roles."""
        roles = []

        if not os.path.exists(self.roles_path):
            return roles

        try:
            for role_name in os.listdir(self.roles_path):
                role_path = os.path.join(self.roles_path, role_name)
                if not os.path.isdir(role_path) or role_name.startswith('.'):
                    continue

                version = "unknown"
                meta_path = os.path.join(role_path, 'meta', 'main.yml')
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = yaml.safe_load(f) or {}
                            if isinstance(meta, dict) and 'galaxy_info' in meta:
                                version = meta['galaxy_info'].get('version', 'unknown')
                    except Exception:
                        pass

                roles.append(RoleInfo(
                    name=role_name,
                    version=version,
                    path=role_path
                ))
        except OSError as e:
            logger.error("Error listing roles: %s", e)

        roles.sort(key=lambda r: r.name)
        return roles

    def get_collection(self, fqcn: str) -> Optional[CollectionInfo]:
        """Get details for a specific collection via direct path lookup."""
        parts = fqcn.split('.', 1)
        if len(parts) != 2:
            return None

        namespace, name = parts
        base_path = self._get_collections_base_path()
        collection_path = os.path.join(base_path, namespace, name)

        if not os.path.isdir(collection_path):
            return None

        manifest = self._read_collection_manifest(collection_path)
        version = "unknown"

        if manifest and 'collection_info' in manifest:
            version = manifest['collection_info'].get('version', 'unknown')
        else:
            galaxy_data = self._read_galaxy_yml(collection_path)
            version = galaxy_data.get('version', 'unknown')

        modules = self._get_collection_modules(collection_path)

        return CollectionInfo(
            namespace=namespace,
            name=name,
            fqcn=fqcn,
            version=version,
            path=collection_path,
            modules=modules
        )

    def get_role(self, name: str) -> Optional[RoleInfo]:
        """Get details for a specific role via direct path lookup."""
        role_path = os.path.join(self.roles_path, name)

        if not os.path.isdir(role_path) or name.startswith('.'):
            return None

        version = "unknown"
        meta_path = os.path.join(role_path, 'meta', 'main.yml')
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = yaml.safe_load(f) or {}
                    if isinstance(meta, dict) and 'galaxy_info' in meta:
                        version = meta['galaxy_info'].get('version', 'unknown')
            except Exception:
                pass

        return RoleInfo(
            name=name,
            version=version,
            path=role_path
        )

    # ========== INSTALLATION ==========

    def _run_galaxy_command(self, args: List[str]) -> Tuple[bool, str, str]:
        """Run an ansible-galaxy command."""
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
        """Install a collection from Ansible Galaxy."""
        try:
            name = self.validate_collection_name(name)
        except ValueError as e:
            return {'success': False, 'output': '', 'error': str(e)}

        target = name
        if version:
            target = f"{name}:{version}"

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
        """Install a role from Ansible Galaxy."""
        try:
            name = self.validate_role_name(name)
        except ValueError as e:
            return {'success': False, 'output': '', 'error': str(e)}

        target = name
        if version:
            target = f"{name},{version}"

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
        """Delete an installed collection."""
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
        """Delete an installed role."""
        role = self.get_role(name)
        if not role:
            return {'success': False, 'error': f"Role '{name}' not found"}

        try:
            shutil.rmtree(role.path)
            return {'success': True, 'error': ''}
        except OSError as e:
            return {'success': False, 'error': str(e)}

    # ========== REQUIREMENTS EXPORT/IMPORT ==========

    def export_requirements_yaml(self) -> str:
        """Export installed collections and roles as requirements.yml content."""
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
        """Import and install collections and roles from requirements.yml content."""
        try:
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
