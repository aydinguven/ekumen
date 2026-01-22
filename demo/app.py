"""
Ekumen - Demo App
A simulated version of Ekumen for demonstration purposes.
"""

from flask import Flask, render_template, request, jsonify, Response
from mock_runner import MockRunner
import os
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'demo-secret-key'

runner = MockRunner()

# Store last output logic (simplified)
last_output = {'content': '', 'timestamp': None}

@app.route('/')
def index():
    """Serve the main single-page application."""
    # Hardcoded version for demo
    return render_template('index.html', ansible_available=True, version="DEMO-MODE", is_demo=True)

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

if __name__ == '__main__':
    print(f"🚀 Ekumen DEMO starting...")
    print(f"   Access at http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
