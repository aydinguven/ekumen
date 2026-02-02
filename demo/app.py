"""
Ekumen - Web Application (DEMO VERSION)
A Flask-based single-page app for running Ansible playbooks and ad-hoc commands.
This is a DEMO version with simulated backend.
"""

from flask import Flask, render_template, request, jsonify, Response
from mock_runner import MockAnsibleRunner
from config import Config
import os
import re
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Initialize Mock Runner
runner = MockAnsibleRunner()

# Store last output for download (simple in-memory cache)
last_output = {'content': '', 'timestamp': None}


@app.route('/')
def index():
    """Serve the main single-page application."""
    return render_template('index.html', ansible_available=runner.ansible_available, version=f"{Config.VERSION} (DEMO)")


@app.route('/run', methods=['POST'])
def run_ansible():
    """Execute Ansible ad-hoc command or playbook."""
    global last_output
    
    data = request.get_json()
    
    # Basic input validation
    if not data:
        return jsonify({'success': False, 'output': '', 'error': 'Invalid request data'})
    
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


# ========== PLAYBOOK LIBRARY (Simulated) ==========

# Use a local demo_playbooks folder relative to this file
DEMO_PLAYBOOK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo_playbooks')

# Ensure demo playbooks exist
if not os.path.exists(DEMO_PLAYBOOK_DIR):
    try:
        os.makedirs(DEMO_PLAYBOOK_DIR, exist_ok=True)
        # Create some sample playbooks
        with open(os.path.join(DEMO_PLAYBOOK_DIR, 'webserver_setup.yml'), 'w') as f:
            f.write("""---
- name: Webserver Setup
  hosts: all
  tasks:
    - name: Install Nginx
      yum:
        name: nginx
        state: present
    
    - name: Ensure Nginx is running
      service:
        name: nginx
        state: started
        enabled: true
""")
        with open(os.path.join(DEMO_PLAYBOOK_DIR, 'database_backup.yml'), 'w') as f:
            f.write("""---
- name: Database Backup
  hosts: db_servers
  tasks:
    - name: Dump database
      shell: pg_dump dbname > /tmp/db_$(date +%F).sql
      
    - name: Archive backup
      archive:
        path: /tmp/db_*.sql
        dest: /backups/db_backup.tar.gz
""")
        with open(os.path.join(DEMO_PLAYBOOK_DIR, 'system_update.yml'), 'w') as f:
            f.write("""---
- name: System Update
  hosts: all
  tasks:
    - name: Update all packages
      yum:
        name: '*'
        state: latest
      
    - name: Reboot if kernel updated
      reboot:
        msg: "Rebooting for kernel update"
        test_command: whoami
""")
    except Exception as e:
        print(f"Warning: Could not create demo playbooks: {e}")

# ========== INVENTORY LIBRARY (Simulated) ==========

# Use a local demo_inventories folder relative to this file
DEMO_INVENTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo_inventories')

# Ensure demo inventories exist
if not os.path.exists(DEMO_INVENTORY_DIR):
    try:
        os.makedirs(DEMO_INVENTORY_DIR, exist_ok=True)
        # Create a sample inventory
        with open(os.path.join(DEMO_INVENTORY_DIR, 'production.ini'), 'w') as f:
            f.write("""[webservers]
192.168.1.10
192.168.1.11

[database]
db.example.com
192.168.1.20

[all:vars]
ansible_user=opc
ansible_port=22
""")
        with open(os.path.join(DEMO_INVENTORY_DIR, 'staging.ini'), 'w') as f:
            f.write("""[staging]
test-web.example.com
test-db.example.com
""")
    except Exception as e:
        print(f"Warning: Could not create demo inventories: {e}")

def get_inventory_dir():
    return DEMO_INVENTORY_DIR

def sanitize_inventory_name(name):
    """Sanitize inventory name."""
    name = re.sub(r'[/\\:*?"<>|]', '', name)
    if not name.endswith('.ini'):
        name += '.ini'
    return name

@app.route('/inventories', methods=['GET'])
def list_inventories():
    """List all saved inventories."""
    inv_dir = get_inventory_dir()
    if not os.path.exists(inv_dir):
        return jsonify({'inventories': []})
    
    inventories = []
    try:
        for f in os.listdir(inv_dir):
            if f.endswith('.ini'):
                inventories.append(f)
    except OSError:
        pass
    
    inventories.sort()
    return jsonify({'inventories': inventories})


@app.route('/inventories/<name>', methods=['GET'])
def get_inventory(name):
    """Get inventory content by name."""
    inv_dir = get_inventory_dir()
    safe_name = sanitize_inventory_name(name)
    path = os.path.join(inv_dir, safe_name)
    
    if not os.path.exists(path):
        return jsonify({'success': False, 'error': 'Inventory not found'}), 404
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'success': True, 'name': safe_name, 'content': content})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/inventories', methods=['POST'])
def save_inventory():
    """Save a new inventory."""
    data = request.get_json()
    if not data or 'name' not in data or 'content' not in data:
        return jsonify({'success': False, 'error': 'Name and content required'}), 400

    inv_dir = get_inventory_dir()
    safe_name = sanitize_inventory_name(data['name'])
    path = os.path.join(inv_dir, safe_name)
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data['content'])
        return jsonify({'success': True, 'name': safe_name})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/inventories/<name>', methods=['DELETE'])
def delete_inventory(name):
    """Delete an inventory."""
    inv_dir = get_inventory_dir()
    safe_name = sanitize_inventory_name(name)
    path = os.path.join(inv_dir, safe_name)
    
    if not os.path.exists(path):
        return jsonify({'success': False, 'error': 'Inventory not found'}), 404
    
    try:
        os.remove(path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def get_playbook_dir():
    return DEMO_PLAYBOOK_DIR

def sanitize_filename(name):
    """Sanitize filename to prevent path traversal."""
    # Remove path separators and dangerous characters
    name = re.sub(r'[/\\:*?"<>|]', '', name)
    # Ensure .yml extension
    if not name.endswith('.yml') and not name.endswith('.yaml'):
        name += '.yml'
    return name

@app.route('/playbooks', methods=['GET'])
def list_playbooks():
    """List all saved playbooks."""
    playbook_dir = get_playbook_dir()
    if not os.path.exists(playbook_dir):
        return jsonify({'playbooks': []})
    
    playbooks = []
    try:
        for f in os.listdir(playbook_dir):
            if f.endswith('.yml') or f.endswith('.yaml'):
                playbooks.append(f)
    except OSError:
        pass
    
    playbooks.sort()
    return jsonify({'playbooks': playbooks})

@app.route('/playbooks/<name>', methods=['GET'])
def get_playbook(name):
    """Get playbook content by name."""
    playbook_dir = get_playbook_dir()
    safe_name = sanitize_filename(name)
    path = os.path.join(playbook_dir, safe_name)
    
    if not os.path.exists(path):
        return jsonify({'success': False, 'error': 'Playbook not found'}), 404
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'success': True, 'name': safe_name, 'content': content})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/playbooks', methods=['POST'])
def save_playbook():
    """Save a new playbook."""
    data = request.get_json()
    if not data or 'name' not in data or 'content' not in data:
        return jsonify({'success': False, 'error': 'Name and content required'}), 400
    
    playbook_dir = get_playbook_dir()
    safe_name = sanitize_filename(data['name'])
    path = os.path.join(playbook_dir, safe_name)
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data['content'])
        return jsonify({'success': True, 'name': safe_name})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/playbooks/<name>', methods=['DELETE'])
def delete_playbook(name):
    """Delete a playbook."""
    playbook_dir = get_playbook_dir()
    safe_name = sanitize_filename(name)
    path = os.path.join(playbook_dir, safe_name)
    
    if not os.path.exists(path):
        return jsonify({'success': False, 'error': 'Playbook not found'}), 404
    
    try:
        os.remove(path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print(f"🚀 Ekumen DEMO starting...")
    print(f"   Mode: SIMULATED (No real Ansible execution)")
    print(f"   Host: {Config.HOST}:{Config.PORT}")
    app.run(debug=True, host=Config.HOST, port=Config.PORT)
