"""
Ekumen - Inventory Manager
Handles storage and retrieval of Ansible inventory files.
"""

import os
import re


class InventoryManager:
    """Manages saved Ansible inventories."""

    def __init__(self, inventory_dir):
        self.inventory_dir = inventory_dir
        self._ensure_dir()

    def _ensure_dir(self):
        """Create inventory directory if it doesn't exist."""
        if not os.path.exists(self.inventory_dir):
            try:
                os.makedirs(self.inventory_dir, exist_ok=True)
            except OSError:
                pass  # May fail on read-only filesystem

    def _sanitize_name(self, name):
        """Sanitize inventory name to prevent path traversal."""
        # Remove path separators and dangerous characters
        name = re.sub(r'[/\\:*?"<>|]', '', name)
        # Ensure .ini extension for inventory files
        if not name.endswith('.ini'):
            name += '.ini'
        return name

    def list_inventories(self):
        """List all saved inventories."""
        if not os.path.exists(self.inventory_dir):
            return []

        inventories = []
        for f in os.listdir(self.inventory_dir):
            if f.endswith('.ini'):
                inventories.append(f)

        inventories.sort()
        return inventories

    def get_inventory(self, name):
        """Get inventory content by name. Returns (success, content_or_error)."""
        safe_name = self._sanitize_name(name)
        path = os.path.join(self.inventory_dir, safe_name)

        if not os.path.exists(path):
            return False, 'Inventory not found'

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return True, content
        except Exception as e:
            return False, str(e)

    def save_inventory(self, name, content):
        """Save an inventory. Returns (success, name_or_error)."""
        self._ensure_dir()
        safe_name = self._sanitize_name(name)
        path = os.path.join(self.inventory_dir, safe_name)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, safe_name
        except Exception as e:
            return False, str(e)

    def delete_inventory(self, name):
        """Delete an inventory. Returns (success, error_or_none)."""
        safe_name = self._sanitize_name(name)
        path = os.path.join(self.inventory_dir, safe_name)

        if not os.path.exists(path):
            return False, 'Inventory not found'

        try:
            os.remove(path)
            return True, None
        except Exception as e:
            return False, str(e)
