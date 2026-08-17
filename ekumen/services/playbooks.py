"""
Ekumen - Playbook Manager Service
Handles secure storage, retrieval, and validation of Ansible playbook files.
"""

import logging
import os
import re
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = ('.yml', '.yaml')


class PlaybookManager:
    """Manages saved Ansible playbooks on filesystem."""

    def __init__(self, playbook_dir: str):
        self.playbook_dir = os.path.abspath(playbook_dir)
        self._ensure_dir()

    def _ensure_dir(self):
        """Create playbook directory if it doesn't exist."""
        if not os.path.exists(self.playbook_dir):
            try:
                os.makedirs(self.playbook_dir, exist_ok=True)
            except OSError as e:
                logger.warning("Could not create playbook directory %s: %s", self.playbook_dir, e)

    def sanitize_name(self, name: str) -> str:
        """
        Sanitize playbook name to prevent path traversal and ensure valid filename.
        """
        if not name or not isinstance(name, str):
            raise ValueError("Playbook name cannot be empty")

        # Get base filename first to strip directory paths
        base = os.path.basename(name.replace('\\', '/').rstrip('/'))
        cleaned = re.sub(r'[/\\:*?"<>|]', '', base).strip().lstrip('.')

        if not cleaned:
            raise ValueError("Invalid playbook name")

        # Ensure .yml extension if neither .yml nor .yaml is present
        if not any(cleaned.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
            cleaned += '.yml'

        return cleaned

    def _get_safe_path(self, name: str) -> Tuple[str, str]:
        """Resolve path and verify it stays inside playbook_dir."""
        safe_name = self.sanitize_name(name)
        full_path = os.path.abspath(os.path.join(self.playbook_dir, safe_name))

        # Path traversal guard
        common = os.path.commonpath([self.playbook_dir, full_path])
        if common != self.playbook_dir:
            raise ValueError("Path traversal attempt detected")

        return full_path, safe_name

    def list_playbooks(self) -> List[str]:
        """List all saved playbooks sorted alphabetically."""
        if not os.path.exists(self.playbook_dir):
            return []

        playbooks = []
        try:
            for f in os.listdir(self.playbook_dir):
                if any(f.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS) and not f.startswith('.'):
                    full_path = os.path.join(self.playbook_dir, f)
                    if os.path.isfile(full_path):
                        playbooks.append(f)
        except OSError as e:
            logger.error("Failed to list playbooks: %s", e)

        playbooks.sort(key=lambda s: s.lower())
        return playbooks

    def get_playbook(self, name: str) -> Tuple[bool, str]:
        """
        Get playbook content by name.
        Returns: (success: bool, content_or_error: str)
        """
        try:
            full_path, safe_name = self._get_safe_path(name)
        except ValueError as e:
            return False, str(e)

        if not os.path.exists(full_path):
            return False, f"Playbook '{safe_name}' not found"

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return True, content
        except Exception as e:
            logger.error("Failed to read playbook %s: %s", safe_name, e)
            return False, str(e)

    def save_playbook(self, name: str, content: str) -> Tuple[bool, str]:
        """
        Save a playbook.
        Returns: (success: bool, saved_name_or_error: str)
        """
        self._ensure_dir()
        try:
            full_path, safe_name = self._get_safe_path(name)
        except ValueError as e:
            return False, str(e)

        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, safe_name
        except Exception as e:
            logger.error("Failed to save playbook %s: %s", safe_name, e)
            return False, str(e)

    def delete_playbook(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a playbook.
        Returns: (success: bool, error_or_none: Optional[str])
        """
        try:
            full_path, safe_name = self._get_safe_path(name)
        except ValueError as e:
            return False, str(e)

        if not os.path.exists(full_path):
            return False, f"Playbook '{safe_name}' not found"

        try:
            os.remove(full_path)
            return True, None
        except Exception as e:
            logger.error("Failed to delete playbook %s: %s", safe_name, e)
            return False, str(e)
