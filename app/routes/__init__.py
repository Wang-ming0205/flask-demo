"""Blueprint registration.

The legacy UI blueprint is a single Blueprint named `main` that includes all UI
routes. It must be registered only once.
"""

from ._legacy import main as main_bp
from ._legacy import api as api_bp


def register_blueprints(app):
    # UI (auth/dashboard/equipment/admin) - legacy single blueprint
    app.register_blueprint(main_bp)

    # API
    app.register_blueprint(api_bp, url_prefix="/api")
