from flask import jsonify, request
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    """Register app-level error handlers.

    The API blueprint already has JSON handlers in routes/_legacy.py.
    This layer is a safe fallback for unexpected errors.
    """

    @app.errorhandler(HTTPException)
    def handle_http(e: HTTPException):
        # Keep UI behavior unchanged (Werkzeug default pages) unless it's API.
        if request.path.startswith("/api"):
            return jsonify(error={"code": e.name, "message": e.description}), e.code
        return e

    @app.errorhandler(Exception)
    def handle_unexpected(e: Exception):
        app.logger.exception("Unhandled error")
        if request.path.startswith("/api"):
            return jsonify(error={"code": "INTERNAL_SERVER_ERROR", "message": "unexpected server error"}), 500
        raise
