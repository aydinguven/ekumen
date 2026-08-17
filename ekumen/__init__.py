"""
Ekumen - Application Factory
"""

import logging
import os
from flask import Flask

from ekumen.config import Config
from ekumen.services.runner import AnsibleRunner
from ekumen.services.inventories import InventoryManager
from ekumen.services.playbooks import PlaybookManager
from ekumen.services.collections import CollectionManager
from ekumen.services.output_cache import OutputCache
from ekumen.api import runner_bp, playbooks_bp, inventories_bp, collections_bp
from ekumen.web import web_bp


def create_app(config_object=None) -> Flask:
    """
    Application factory for Ekumen.
    """
    # Determine base directory (project root containing static and templates)
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(pkg_dir)

    template_dir = os.path.join(project_root, 'templates')
    static_dir = os.path.join(project_root, 'static')

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir
    )

    # Load configuration
    cfg = config_object or Config
    app.config['SECRET_KEY'] = cfg.SECRET_KEY
    app.config['EKUMEN_CONFIG'] = cfg

    # Configure logging
    log_level = logging.DEBUG if cfg.DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

    # Initialize Services
    runner = AnsibleRunner(
        allowed_modules=cfg.ALLOWED_MODULES,
        collections_path=cfg.COLLECTIONS_PATH,
        roles_path=cfg.ROLES_PATH,
        command_timeout=cfg.COMMAND_TIMEOUT,
        ssh_timeout=cfg.SSH_CONNECT_TIMEOUT
    )
    inventory_manager = InventoryManager(cfg.INVENTORY_DIR)
    playbook_manager = PlaybookManager(cfg.PLAYBOOK_DIR)
    collection_manager = CollectionManager(
        collections_path=cfg.COLLECTIONS_PATH,
        roles_path=cfg.ROLES_PATH,
        timeout=cfg.GALAXY_TIMEOUT
    )
    output_cache = OutputCache(cache_dir=cfg.OUTPUT_CACHE_DIR)

    # Store in app extensions
    app.extensions['ekumen'] = {
        'runner': runner,
        'inventory_manager': inventory_manager,
        'playbook_manager': playbook_manager,
        'collection_manager': collection_manager,
        'output_cache': output_cache,
    }

    # Register Blueprints
    app.register_blueprint(web_bp)
    app.register_blueprint(runner_bp)
    app.register_blueprint(playbooks_bp)
    app.register_blueprint(inventories_bp)
    app.register_blueprint(collections_bp)

    return app
