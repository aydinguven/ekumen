"""
Ekumen - Web Application
A Flask-based single-page app for running Ansible playbooks and ad-hoc commands.
"""

import datetime
import logging

from flask import Flask, render_template, request, jsonify, Response
from ansible_runner import AnsibleRunner
from inventory_manager import InventoryManager
from playbook_manager import PlaybookManager
from collection_manager import CollectionManager
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if Config.DEBUG else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

runner = AnsibleRunner()
inventory_manager = InventoryManager(Config.INVENTORY_DIR)
playbook_manager = PlaybookManager(Config.PLAYBOOK_DIR)
collection_manager = CollectionManager(
    collections_path=Config.COLLECTIONS_PATH,
    roles_path=Config.ROLES_PATH,
    timeout=Config.GALAXY_TIMEOUT
)

# Store last output for download (simple in-memory cache)
last_output = {'content': '', 'timestamp': None}


@app.route('/')
def index():
    """Serve the main single-page application."""
    return render_template('index.html', ansible_available=runner.ansible_available, version=Config.VERSION)


@app.route('/run', methods=['POST'])
def run_ansible():
    """Execute Ansible ad-hoc command or playbook."""
    global last_output
    
    data = request.get_json()
    
    # Basic input validation
    if not data:
        return jsonify({'success': False, 'output': '', 'error': 'Invalid request data'})
    
    logger.info("Running %s command", data.get('mode', 'adhoc'))
    result = runner.run(data)
    
    # Store output for download
    output_text = result.get('output', '')
    if result.get('error'):
        output_text += f"\n\n--- STDERR ---\n{result['error']}"
    
    last_output = {
        'content': output_text,
        'timestamp': datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    }
    
    return jsonify(result)


@app.route('/download')
def download_output():
    """Download the last command output as a text file."""
    if not last_output['content']:
        return Response("No output available", mimetype='text/plain')
    
    filename = f"ansible_output_{last_output['timestamp']}.txt"
    
    return Response(
        last_output['content'],
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


# ========== PLAYBOOK LIBRARY ==========

@app.route('/playbooks', methods=['GET'])
def list_playbooks():
    """List all saved playbooks."""
    playbooks = playbook_manager.list_playbooks()
    return jsonify({'playbooks': playbooks})


@app.route('/playbooks/<name>', methods=['GET'])
def get_playbook(name):
    """Get playbook content by name."""
    success, result = playbook_manager.get_playbook(name)
    if not success:
        return jsonify({'success': False, 'error': result}), 404
    return jsonify({'success': True, 'name': playbook_manager._sanitize_name(name), 'content': result})


@app.route('/playbooks', methods=['POST'])
def save_playbook():
    """Save a new playbook."""
    data = request.get_json()
    if not data or 'name' not in data or 'content' not in data:
        return jsonify({'success': False, 'error': 'Name and content required'}), 400

    success, result = playbook_manager.save_playbook(data['name'], data['content'])
    if not success:
        return jsonify({'success': False, 'error': result}), 500
    return jsonify({'success': True, 'name': result})


@app.route('/playbooks/<name>', methods=['DELETE'])
def delete_playbook(name):
    """Delete a playbook."""
    success, error = playbook_manager.delete_playbook(name)
    if not success:
        return jsonify({'success': False, 'error': error}), 404
    return jsonify({'success': True})


# ========== INVENTORY LIBRARY ==========

@app.route('/inventories', methods=['GET'])
def list_inventories():
    """List all saved inventories."""
    inventories = inventory_manager.list_inventories()
    return jsonify({'inventories': inventories})


@app.route('/inventories/<name>', methods=['GET'])
def get_inventory(name):
    """Get inventory content by name."""
    success, result = inventory_manager.get_inventory(name)
    if not success:
        return jsonify({'success': False, 'error': result}), 404
    return jsonify({'success': True, 'name': name, 'content': result})


@app.route('/inventories', methods=['POST'])
def save_inventory():
    """Save a new inventory."""
    data = request.get_json()
    if not data or 'name' not in data or 'content' not in data:
        return jsonify({'success': False, 'error': 'Name and content required'}), 400

    success, result = inventory_manager.save_inventory(data['name'], data['content'])
    if not success:
        return jsonify({'success': False, 'error': result}), 500
    return jsonify({'success': True, 'name': result})


@app.route('/inventories/<name>', methods=['DELETE'])
def delete_inventory(name):
    """Delete an inventory."""
    success, error = inventory_manager.delete_inventory(name)
    if not success:
        return jsonify({'success': False, 'error': error}), 404
    return jsonify({'success': True})


# ========== COLLECTIONS API ==========

@app.route('/collections', methods=['GET'])
def list_collections():
    """List all installed collections."""
    collections = collection_manager.list_collections()
    return jsonify({
        'collections': [c.to_dict() for c in collections],
        'galaxy_available': collection_manager.galaxy_available
    })


@app.route('/collections/<path:fqcn>', methods=['GET'])
def get_collection(fqcn):
    """Get collection details by FQCN."""
    collection = collection_manager.get_collection(fqcn)
    if not collection:
        return jsonify({'success': False, 'error': 'Collection not found'}), 404
    return jsonify({'success': True, 'collection': collection.to_dict()})


@app.route('/collections', methods=['POST'])
def install_collection():
    """Install a collection from Ansible Galaxy."""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'success': False, 'error': 'Collection name required'}), 400
    
    logger.info("Installing collection: %s", data['name'])
    result = collection_manager.install_collection(
        name=data['name'],
        version=data.get('version'),
        force=data.get('force', False)
    )
    
    status_code = 200 if result['success'] else 500
    return jsonify(result), status_code


@app.route('/collections/<path:fqcn>', methods=['DELETE'])
def delete_collection(fqcn):
    """Delete an installed collection."""
    result = collection_manager.delete_collection(fqcn)
    status_code = 200 if result['success'] else 404
    return jsonify(result), status_code


# ========== ROLES API ==========

@app.route('/roles', methods=['GET'])
def list_roles():
    """List all installed roles."""
    roles = collection_manager.list_roles()
    return jsonify({
        'roles': [r.to_dict() for r in roles],
        'galaxy_available': collection_manager.galaxy_available
    })


@app.route('/roles/<name>', methods=['GET'])
def get_role(name):
    """Get role details by name."""
    role = collection_manager.get_role(name)
    if not role:
        return jsonify({'success': False, 'error': 'Role not found'}), 404
    return jsonify({'success': True, 'role': role.to_dict()})


@app.route('/roles', methods=['POST'])
def install_role():
    """Install a role from Ansible Galaxy."""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'success': False, 'error': 'Role name required'}), 400
    
    logger.info("Installing role: %s", data['name'])
    result = collection_manager.install_role(
        name=data['name'],
        version=data.get('version'),
        force=data.get('force', False)
    )
    
    status_code = 200 if result['success'] else 500
    return jsonify(result), status_code


@app.route('/roles/<name>', methods=['DELETE'])
def delete_role(name):
    """Delete an installed role."""
    result = collection_manager.delete_role(name)
    status_code = 200 if result['success'] else 404
    return jsonify(result), status_code


# ========== REQUIREMENTS EXPORT/IMPORT ==========

@app.route('/requirements', methods=['GET'])
def export_requirements():
    """Export installed collections and roles as requirements.yml."""
    content = collection_manager.export_requirements_yaml()
    return Response(
        content,
        mimetype='text/yaml',
        headers={'Content-Disposition': 'attachment; filename="requirements.yml"'}
    )


@app.route('/requirements', methods=['POST'])
def import_requirements():
    """Import and install from requirements.yml content."""
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'success': False, 'error': 'No content provided'}), 400
    
    force = data.get('force', False)
    logger.info("Importing requirements (force=%s)", force)
    result = collection_manager.import_requirements_yaml(data['content'], force)
    
    status_code = 200 if result['success'] else 500
    return jsonify(result), status_code


if __name__ == '__main__':
    logger.info("🚀 Ekumen starting...")
    logger.info("   Debug: %s", Config.DEBUG)
    logger.info("   Host: %s:%s", Config.HOST, Config.PORT)
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
