"""
Ekumen - Connectivity & Fact Discovery API Blueprint
"""

import logging
from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

connectivity_bp = Blueprint('connectivity_api', __name__)


def _get_checker():
    return current_app.extensions['ekumen']['connectivity_checker']


@connectivity_bp.route('/connectivity/ping', methods=['POST'])
def test_connectivity():
    """
    Test connectivity (ping) against hosts in the provided inventory.
    """
    checker = _get_checker()
    data = request.get_json(silent=True) or {}

    inventory = str(data.get('inventory', '')).strip()
    if not inventory:
        return jsonify({
            'success': False,
            'error': 'Inventory is required'
        }), 400

    username = str(data.get('username', '')).strip()
    password = str(data.get('password', ''))
    private_key = str(data.get('private_key', '')).strip()
    timeout = min(max(int(data.get('timeout', 5)), 1), 30)

    result = checker.ping_hosts(
        inventory_content=inventory,
        username=username,
        password=password,
        private_key=private_key,
        timeout=timeout
    )

    return jsonify(result)


@connectivity_bp.route('/connectivity/facts', methods=['POST'])
def fetch_host_facts():
    """
    Retrieve structured facts and specs for a specific host.
    """
    checker = _get_checker()
    data = request.get_json(silent=True) or {}

    host = str(data.get('host', '')).strip()
    if not host:
        return jsonify({'success': False, 'error': 'Host parameter is required'}), 400

    inventory = str(data.get('inventory', '')).strip()
    if not inventory:
        inventory = host  # Fallback to single host inventory

    username = str(data.get('username', '')).strip()
    password = str(data.get('password', ''))
    private_key = str(data.get('private_key', '')).strip()
    timeout = min(max(int(data.get('timeout', 15)), 2), 60)

    result = checker.get_host_facts(
        hostname=host,
        inventory_content=inventory,
        username=username,
        password=password,
        private_key=private_key,
        timeout=timeout
    )

    if not result.get('success'):
        return jsonify(result), 400

    return jsonify(result)
