"""
Ekumen - Inventories API Blueprint
Handles Inventory Library CRUD operations.
"""

import logging
from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

inventories_bp = Blueprint('inventories_api', __name__)


def _get_manager():
    return current_app.extensions['ekumen']['inventory_manager']


@inventories_bp.route('/inventories', methods=['GET'])
def list_inventories():
    """List all saved inventories."""
    manager = _get_manager()
    inventories = manager.list_inventories()
    return jsonify({'inventories': inventories})


@inventories_bp.route('/inventories/<name>', methods=['GET'])
def get_inventory(name):
    """Get inventory content by name."""
    manager = _get_manager()
    success, result = manager.get_inventory(name)
    if not success:
        return jsonify({'success': False, 'error': result}), 404

    try:
        safe_name = manager.sanitize_name(name)
    except ValueError:
        safe_name = name

    return jsonify({
        'success': True,
        'name': safe_name,
        'content': result
    })


@inventories_bp.route('/inventories', methods=['POST'])
def save_inventory():
    """Save a new or existing inventory."""
    manager = _get_manager()
    data = request.get_json(silent=True)
    if not data or 'name' not in data or 'content' not in data:
        return jsonify({'success': False, 'error': 'Name and content are required fields.'}), 400

    name = str(data['name']).strip()
    content = str(data['content'])

    if not name:
        return jsonify({'success': False, 'error': 'Inventory name cannot be empty.'}), 400

    success, result = manager.save_inventory(name, content)
    if not success:
        return jsonify({'success': False, 'error': result}), 500

    return jsonify({'success': True, 'name': result})


@inventories_bp.route('/inventories/<name>', methods=['DELETE'])
def delete_inventory(name):
    """Delete an inventory."""
    manager = _get_manager()
    success, error = manager.delete_inventory(name)
    if not success:
        return jsonify({'success': False, 'error': error}), 404

    return jsonify({'success': True})


@inventories_bp.route('/inventories/parse', methods=['POST'])
def parse_inventory_content():
    """Parse raw inventory text and return structured host/group tree."""
    from ekumen.services.inventory_parser import parse_inventory

    data = request.get_json(silent=True) or {}
    content = str(data.get('content', ''))
    parsed = parse_inventory(content)

    return jsonify({'success': True, 'data': parsed})
