"""
Ekumen - Web Application
A Flask-based single-page app for running Ansible playbooks and ad-hoc commands.
"""

from flask import Flask, render_template, request, jsonify, Response
from ansible_runner import AnsibleRunner
from config import Config

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

runner = AnsibleRunner()

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
    
    result = runner.run(data)
    
    # Store output for download
    import datetime
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
import os
import re

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
    if not os.path.exists(playbook_dir):
        return jsonify({'playbooks': []})
    
    playbooks = []
    for f in os.listdir(playbook_dir):
        if f.endswith('.yml') or f.endswith('.yaml'):
            playbooks.append(f)
    
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
    print(f"🚀 Ekumen starting...")
    print(f"   Debug: {Config.DEBUG}")
    print(f"   Host: {Config.HOST}:{Config.PORT}")
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
