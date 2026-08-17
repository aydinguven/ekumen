"""
Ekumen - Jobs & Streaming API Blueprint
Handles asynchronous execution, Server-Sent Events (SSE) streaming, cancellation, and SQLite history.
"""

import logging
from flask import Blueprint, request, jsonify, Response, current_app

logger = logging.getLogger(__name__)

jobs_bp = Blueprint('jobs_api', __name__)


def _get_job_manager():
    return current_app.extensions['ekumen']['job_manager']


def _get_db():
    return current_app.extensions['ekumen']['db']


@jobs_bp.route('/jobs', methods=['POST'])
def start_job():
    """Start an asynchronous execution job and return stream URL."""
    job_mgr = _get_job_manager()
    data = request.get_json(silent=True)

    if not data:
        return jsonify({'success': False, 'error': 'Invalid or empty JSON request payload'}), 400

    inventory = str(data.get('inventory', '')).strip()
    if not inventory:
        return jsonify({'success': False, 'error': 'Inventory is required'}), 400

    job_id = job_mgr.start_job(data)

    return jsonify({
        'success': True,
        'job_id': job_id,
        'stream_url': f'/jobs/{job_id}/stream'
    })


@jobs_bp.route('/jobs/<job_id>/stream', methods=['GET'])
def stream_job(job_id):
    """Server-Sent Events (SSE) live streaming endpoint."""
    job_mgr = _get_job_manager()

    return Response(
        job_mgr.subscribe(job_id),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@jobs_bp.route('/jobs/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    """Cancel an actively running job."""
    job_mgr = _get_job_manager()
    success = job_mgr.cancel_job(job_id)

    if not success:
        return jsonify({'success': False, 'error': 'Job not running or already completed'}), 400

    return jsonify({'success': True, 'message': 'Cancellation signal sent'})


@jobs_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List execution history from SQLite database."""
    db = _get_db()
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))

    jobs = db.list_jobs(limit=limit, offset=offset)
    return jsonify({'jobs': jobs, 'limit': limit, 'offset': offset})


@jobs_bp.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get full details of a specific job run."""
    db = _get_db()
    job = db.get_job(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404

    return jsonify({'success': True, 'job': job})


@jobs_bp.route('/jobs/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    """Delete a job record from history."""
    db = _get_db()
    success = db.delete_job(job_id)
    if not success:
        return jsonify({'success': False, 'error': 'Job not found'}), 404

    return jsonify({'success': True})


@jobs_bp.route('/jobs', methods=['DELETE'])
def clear_all_jobs():
    """Clear all execution history."""
    db = _get_db()
    db.clear_jobs()
    return jsonify({'success': True, 'message': 'All job history cleared'})
