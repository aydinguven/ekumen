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
    return render_template('index.html', ansible_available=runner.ansible_available)


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


if __name__ == '__main__':
    print(f"🚀 Ekumen starting...")
    print(f"   Debug: {Config.DEBUG}")
    print(f"   Host: {Config.HOST}:{Config.PORT}")
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
