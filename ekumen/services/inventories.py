"""
Ekumen - Inventory Manager Service
Handles secure storage, retrieval, and validation of Ansible inventory files.
"""

import logging
import os
import re
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = ('.ini', '.yaml', '.yml', '.hosts', '.txt')


class InventoryManager:
    """Manages saved Ansible inventories on filesystem."""

    def __init__(self, inventory_dir: str):
        self.inventory_dir = os.path.abspath(inventory_dir)
        self._ensure_dir()

    def _ensure_dir(self):
        """Create inventory directory if it doesn't exist."""
        if not os.path.exists(self.inventory_dir):
            try:
                os.makedirs(self.inventory_dir, exist_ok=True)
            except OSError as e:
                logger.warning("Could not create inventory directory %s: %s", self.inventory_dir, e)

    def sanitize_name(self, name: str) -> str:
        """
        Sanitize inventory name to prevent path traversal and ensure valid filename.
        """
        if not name or not isinstance(name, str):
            raise ValueError("Inventory name cannot be empty")

        # Get base filename first to strip directory paths
        base = os.path.basename(name.replace('\\', '/').rstrip('/'))
        cleaned = re.sub(r'[/\\:*?"<>|]', '', base).strip().lstrip('.')

        if not cleaned:
            raise ValueError("Invalid inventory name")

        # Check if already has a valid extension, else default to .ini
        if not any(cleaned.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
            cleaned += '.ini'

        return cleaned

    def _get_safe_path(self, name: str) -> Optional[str]:
        """Resolve path and verify it stays inside inventory_dir."""
        safe_name = self.sanitize_name(name)
        full_path = os.path.abspath(os.path.join(self.inventory_dir, safe_name))

        # Path traversal guard
        common = os.path.commonpath([self.inventory_dir, full_path])
        if common != self.inventory_dir:
            raise ValueError("Path traversal attempt detected")

        return full_path, safe_name

    def list_inventories(self) -> List[str]:
        """List all saved inventories sorted alphabetically."""
        if not os.path.exists(self.inventory_dir):
            return []

        inventories = []
        try:
            for f in os.listdir(self.inventory_dir):
                if any(f.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS) and not f.startswith('.'):
                    full_path = os.path.join(self.inventory_dir, f)
                    if os.path.isfile(full_path):
                        inventories.append(f)
        except OSError as e:
            logger.error("Failed to list inventories: %s", e)

        inventories.sort(key=lambda s: s.lower())
        return inventories

    def get_inventory(self, name: str) -> Tuple[bool, str]:
        """
        Get inventory content by name.
        Returns: (success: bool, content_or_error: str)
        """
        try:
            full_path, safe_name = self._get_safe_path(name)
        except ValueError as e:
            return False, str(e)

        if not os.path.exists(full_path):
            return False, f"Inventory '{safe_name}' not found"

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return True, content
        except Exception as e:
            logger.error("Failed to read inventory %s: %s", safe_name, e)
            return False, str(e)

    def save_inventory(self, name: str, content: str) -> Tuple[bool, str]:
        """
        Save an inventory.
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
            logger.error("Failed to save inventory %s: %s", safe_name, e)
            return False, str(e)

    def delete_inventory(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        Delete an inventory.
        Returns: (success: bool, error_or_none: Optional[str])
        """
        try:
            full_path, safe_name = self._get_safe_path(name)
        except ValueError as e:
            return False, str(e)

        if not os.path.exists(full_path):
            return False, f"Inventory '{safe_name}' not found"

        try:
            os.remove(full_path)
            return True, None
        except Exception as e:
            logger.error("Failed to delete inventory %s: %s", safe_name, e)
            return False, str(e)
