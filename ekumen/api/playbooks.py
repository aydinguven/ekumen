"""
Ekumen - Playbooks API Blueprint
Handles Playbook Library CRUD operations.
"""

import logging
from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

playbooks_bp = Blueprint('playbooks_api', __name__)


def _get_manager():
    return current_app.extensions['ekumen']['playbook_manager']


@playbooks_bp.route('/playbooks', methods=['GET'])
def list_playbooks():
    """List all saved playbooks."""
    manager = _get_manager()
    playbooks = manager.list_playbooks()
    return jsonify({'playbooks': playbooks})


@playbooks_bp.route('/playbooks/<name>', methods=['GET'])
def get_playbook(name):
    """Get playbook content by name."""
    manager = _get_manager()
    success, result = manager.get_playbook(name)
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


@playbooks_bp.route('/playbooks', methods=['POST'])
def save_playbook():
    """Save a new or existing playbook."""
    manager = _get_manager()
    data = request.get_json(silent=True)
    if not data or 'name' not in data or 'content' not in data:
        return jsonify({'success': False, 'error': 'Name and content are required fields.'}), 400

    name = str(data['name']).strip()
    content = str(data['content'])

    if not name:
        return jsonify({'success': False, 'error': 'Playbook name cannot be empty.'}), 400

    success, result = manager.save_playbook(name, content)
    if not success:
        return jsonify({'success': False, 'error': result}), 500

    return jsonify({'success': True, 'name': result})


@playbooks_bp.route('/playbooks/<name>', methods=['DELETE'])
def delete_playbook(name):
    """Delete a playbook."""
    manager = _get_manager()
    success, error = manager.delete_playbook(name)
    if not success:
        return jsonify({'success': False, 'error': error}), 404

    return jsonify({'success': True})
