"""
Ekumen - Demo App
A simulated version of Ekumen for demonstration purposes.
"""

from flask import Flask, render_template, request, jsonify, Response
from mock_runner import MockRunner
from config import Config
import os
import datetime
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'demo-secret-key'

runner = MockRunner()

# Store last output logic (simplified)
last_output = {'content': '', 'timestamp': None}

@app.route('/')
def index():
    """Serve the main single-page application."""
    # Hardcoded version for demo
    return render_template('index.html', ansible_available=True, version=Config.VERSION, is_demo=True)

@app.route('/run', methods=['POST'])
def run_ansible():
    """Execute simulated Ansible command."""
    global last_output
    
    data = request.get_json()
    result = runner.run(data)
    
    # Store output for download
    last_output = {
        'content': result.get('output', ''),
        'timestamp': datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    }
    
    return jsonify(result)

@app.route('/download')
def download_output():
    """Simulate download."""
    if not last_output['content']:
        return Response("No output available", mimetype='text/plain')
    
    filename = f"demo_output_{last_output['timestamp']}.txt"
    return Response(
        last_output['content'],
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )

# ========== PLAYBOOK LIBRARY ==========

def get_playbook_dir():
    """Get playbook directory, create if not exists."""
    path = Config.PLAYBOOK_DIR
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            pass  # May fail on read-only filesystem
    return path

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
    # Mocking pre-filled playbooks for demo if dir is empty/missing
    if not os.path.exists(playbook_dir):
        return jsonify({'playbooks': []})
    
    playbooks = []
    try:
        for f in os.listdir(playbook_dir):
            if f.endswith('.yml') or f.endswith('.yaml'):
                playbooks.append(f)
    except OSError:
        pass # Handle read-only FS in cloud demos
    
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
        # Create dir if not exists (might fail on read-only cloud demo)
        if not os.path.exists(playbook_dir):
             os.makedirs(playbook_dir, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(data['content'])
        return jsonify({'success': True, 'name': safe_name})
    except Exception as e:
        return jsonify({'success': False, 'error': f"Demo Storage Error: {str(e)}"}), 500

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
    print(f"   Access at http://127.0.0.1:5005")
    app.run(debug=True, host='0.0.0.0', port=5005)
