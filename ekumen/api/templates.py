"""
Ekumen - Playbook Templates API Blueprint
Provides endpoints to list and retrieve built-in playbook templates.
"""

from flask import Blueprint, jsonify
from ekumen.services.templates import list_templates, get_template

templates_bp = Blueprint('templates_api', __name__)


@templates_bp.route('/templates', methods=['GET'])
def get_templates():
    """List all available playbook templates."""
    return jsonify({'templates': list_templates()})


@templates_bp.route('/templates/<template_id>', methods=['GET'])
def get_single_template(template_id):
    """Retrieve template content by ID."""
    tmpl = get_template(template_id)
    if not tmpl:
        return jsonify({'success': False, 'error': 'Template not found'}), 404

    return jsonify({'success': True, 'template': tmpl})
