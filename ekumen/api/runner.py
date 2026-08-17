"""
Ekumen - Runner API Blueprint
Handles execution requests (/run) and output download (/download).
"""

import logging
from flask import Blueprint, request, jsonify, Response, current_app

logger = logging.getLogger(__name__)

runner_bp = Blueprint('runner_api', __name__)


def _get_services():
    return current_app.extensions['ekumen']


@runner_bp.route('/run', methods=['POST'])
def run_ansible():
    """Execute Ansible ad-hoc command or playbook."""
    services = _get_services()
    runner = services['runner']
    output_cache = services['output_cache']

    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            'success': False,
            'output': '',
            'error': 'Invalid or empty JSON request payload.'
        }), 400

    mode = data.get('mode', 'adhoc')
    logger.info("Executing Ansible in mode: %s", mode)

    result = runner.run(data)

    # Store output in cache for download
    output_text = result.get('output', '')
    if result.get('error'):
        if output_text:
            output_text += f"\n\n--- STDERR ---\n{result['error']}"
        else:
            output_text = f"--- ERROR ---\n{result['error']}"

    timestamp_id = output_cache.store(output_text)
    result['run_id'] = timestamp_id

    return jsonify(result)


@runner_bp.route('/download', methods=['GET'])
def download_output():
    """Download the last command output or a specific run as a text file."""
    services = _get_services()
    output_cache = services['output_cache']

    run_id = request.args.get('id', '')
    if run_id:
        content, ts = output_cache.get_by_id(run_id)
    else:
        content, ts = output_cache.get_latest()

    if not content:
        return Response("No output available for download.", mimetype='text/plain', status=404)

    filename = f"ekumen_output_{ts}.txt" if ts else "ekumen_output.txt"

    return Response(
        content,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )
