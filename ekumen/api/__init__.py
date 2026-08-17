"""
Ekumen API Blueprints
"""

from ekumen.api.runner import runner_bp
from ekumen.api.playbooks import playbooks_bp
from ekumen.api.inventories import inventories_bp
from ekumen.api.collections import collections_bp
from ekumen.api.jobs import jobs_bp
from ekumen.api.templates import templates_bp
from ekumen.api.connectivity import connectivity_bp

__all__ = [
    'runner_bp',
    'playbooks_bp',
    'inventories_bp',
    'collections_bp',
    'jobs_bp',
    'templates_bp',
    'connectivity_bp',
]
