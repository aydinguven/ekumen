"""
Ekumen - Web Application Entry Point
A Flask-based single-page application for running Ansible playbooks and ad-hoc commands.
"""

import logging
from ekumen import create_app
from ekumen.config import Config

app = create_app()

if __name__ == '__main__':
    logger = logging.getLogger('ekumen')
    logger.info("🚀 Ekumen starting (v%s)...", Config.VERSION)
    logger.info("   Debug: %s", Config.DEBUG)
    logger.info("   Host: %s:%s", Config.HOST, Config.PORT)
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
