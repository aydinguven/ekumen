"""
Ekumen - Web UI Views Blueprint
Serves the single-page application interface.
"""

from flask import Blueprint, render_template, current_app

web_bp = Blueprint('web', __name__)


@web_bp.route('/')
def index():
    """Serve the main single-page application."""
    services = current_app.extensions['ekumen']
    runner = services['runner']
    config = current_app.config['EKUMEN_CONFIG']

    return render_template(
        'index.html',
        ansible_available=runner.ansible_available,
        version=config.VERSION
    )
