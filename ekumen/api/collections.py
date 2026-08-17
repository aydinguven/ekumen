"""
Ekumen - Collections & Roles API Blueprint
Handles Ansible Galaxy collections, roles, and requirements.yml management.
"""

import logging
from flask import Blueprint, request, jsonify, Response, current_app

logger = logging.getLogger(__name__)

collections_bp = Blueprint('collections_api', __name__)


def _get_manager():
    return current_app.extensions['ekumen']['collection_manager']


# ========== COLLECTIONS ==========

@collections_bp.route('/collections', methods=['GET'])
def list_collections():
    """List all installed collections."""
    manager = _get_manager()
    collections = manager.list_collections()
    return jsonify({
        'collections': [c.to_dict() for c in collections],
        'galaxy_available': manager.galaxy_available
    })


@collections_bp.route('/collections/<path:fqcn>', methods=['GET'])
def get_collection(fqcn):
    """Get collection details by FQCN."""
    manager = _get_manager()
    collection = manager.get_collection(fqcn)
    if not collection:
        return jsonify({'success': False, 'error': f"Collection '{fqcn}' not found"}), 404
    return jsonify({'success': True, 'collection': collection.to_dict()})


@collections_bp.route('/collections', methods=['POST'])
def install_collection():
    """Install a collection from Ansible Galaxy."""
    manager = _get_manager()
    data = request.get_json(silent=True)
    if not data or 'name' not in data:
        return jsonify({'success': False, 'error': 'Collection name is required'}), 400

    name = str(data['name']).strip()
    version = data.get('version')
    force = bool(data.get('force', False))

    logger.info("Installing collection: %s (version=%s, force=%s)", name, version, force)
    result = manager.install_collection(name=name, version=version, force=force)
    status_code = 200 if result.get('success') else 500
    return jsonify(result), status_code


@collections_bp.route('/collections/<path:fqcn>', methods=['DELETE'])
def delete_collection(fqcn):
    """Delete an installed collection."""
    manager = _get_manager()
    result = manager.delete_collection(fqcn)
    status_code = 200 if result.get('success') else 404
    return jsonify(result), status_code


# ========== ROLES ==========

@collections_bp.route('/roles', methods=['GET'])
def list_roles():
    """List all installed roles."""
    manager = _get_manager()
    roles = manager.list_roles()
    return jsonify({
        'roles': [r.to_dict() for r in roles],
        'galaxy_available': manager.galaxy_available
    })


@collections_bp.route('/roles/<name>', methods=['GET'])
def get_role(name):
    """Get role details by name."""
    manager = _get_manager()
    role = manager.get_role(name)
    if not role:
        return jsonify({'success': False, 'error': f"Role '{name}' not found"}), 404
    return jsonify({'success': True, 'role': role.to_dict()})


@collections_bp.route('/roles', methods=['POST'])
def install_role():
    """Install a role from Ansible Galaxy."""
    manager = _get_manager()
    data = request.get_json(silent=True)
    if not data or 'name' not in data:
        return jsonify({'success': False, 'error': 'Role name is required'}), 400

    name = str(data['name']).strip()
    version = data.get('version')
    force = bool(data.get('force', False))

    logger.info("Installing role: %s (version=%s, force=%s)", name, version, force)
    result = manager.install_role(name=name, version=version, force=force)
    status_code = 200 if result.get('success') else 500
    return jsonify(result), status_code


@collections_bp.route('/roles/<name>', methods=['DELETE'])
def delete_role(name):
    """Delete an installed role."""
    manager = _get_manager()
    result = manager.delete_role(name)
    status_code = 200 if result.get('success') else 404
    return jsonify(result), status_code


# ========== REQUIREMENTS EXPORT/IMPORT ==========

@collections_bp.route('/requirements', methods=['GET'])
def export_requirements():
    """Export installed collections and roles as requirements.yml."""
    manager = _get_manager()
    content = manager.export_requirements_yaml()
    return Response(
        content,
        mimetype='text/yaml',
        headers={'Content-Disposition': 'attachment; filename="requirements.yml"'}
    )


@collections_bp.route('/requirements', methods=['POST'])
def import_requirements():
    """Import and install from requirements.yml content."""
    manager = _get_manager()
    data = request.get_json(silent=True)
    if not data or 'content' not in data:
        return jsonify({'success': False, 'error': 'requirements.yml content is required'}), 400

    force = bool(data.get('force', False))
    logger.info("Importing requirements (force=%s)", force)
    result = manager.import_requirements_yaml(data['content'], force=force)
    status_code = 200 if result.get('success') else 500
    return jsonify(result), status_code
