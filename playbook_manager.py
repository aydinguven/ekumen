"""
Ekumen - Playbook Manager
Handles storage and retrieval of Ansible playbook files.
"""

import logging
import os
import re

logger = logging.getLogger(__name__)


class PlaybookManager:
    """Manages saved Ansible playbooks."""

    def __init__(self, playbook_dir):
        self.playbook_dir = playbook_dir
        self._ensure_dir()

    def _ensure_dir(self):
        """Create playbook directory if it doesn't exist."""
        if not os.path.exists(self.playbook_dir):
            try:
                os.makedirs(self.playbook_dir, exist_ok=True)
            except OSError:
                logger.warning("Could not create playbook directory: %s", self.playbook_dir)

    def _sanitize_name(self, name):
        """Sanitize playbook name to prevent path traversal."""
        # Remove path separators and dangerous characters
        name = re.sub(r'[/\\:*?"<>|]', '', name)
        # Ensure .yml extension
        if not name.endswith('.yml') and not name.endswith('.yaml'):
            name += '.yml'
        return name

    def list_playbooks(self):
        """List all saved playbooks. Returns list of filenames."""
        if not os.path.exists(self.playbook_dir):
            return []

        playbooks = []
        for f in os.listdir(self.playbook_dir):
            if f.endswith('.yml') or f.endswith('.yaml'):
                playbooks.append(f)

        playbooks.sort()
        return playbooks

    def get_playbook(self, name):
        """Get playbook content by name. Returns (success, content_or_error)."""
        safe_name = self._sanitize_name(name)
        path = os.path.join(self.playbook_dir, safe_name)

        if not os.path.exists(path):
            return False, 'Playbook not found'

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return True, content
        except Exception as e:
            logger.error("Failed to read playbook %s: %s", safe_name, e)
            return False, str(e)

    def save_playbook(self, name, content):
        """Save a playbook. Returns (success, name_or_error)."""
        self._ensure_dir()
        safe_name = self._sanitize_name(name)
        path = os.path.join(self.playbook_dir, safe_name)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, safe_name
        except Exception as e:
            logger.error("Failed to save playbook %s: %s", safe_name, e)
            return False, str(e)

    def delete_playbook(self, name):
        """Delete a playbook. Returns (success, error_or_none)."""
        safe_name = self._sanitize_name(name)
        path = os.path.join(self.playbook_dir, safe_name)

        if not os.path.exists(path):
            return False, 'Playbook not found'

        try:
            os.remove(path)
            return True, None
        except Exception as e:
            logger.error("Failed to delete playbook %s: %s", safe_name, e)
            return False, str(e)
