import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .config import database_url, parse_duration
from .db import make_database
from .errors import AppError
from .routes import api
from .services import Services

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


def create_app(config=None):
    config = dict(config or {})
    app = Flask(__name__, static_folder=str(FRONTEND), static_url_path="")

    secret = config.get("JWT_SECRET") or os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("Falta JWT_SECRET (defínelo en .env)")
    app.config["JWT_SECRET"] = secret
    expires = parse_duration(config.get("JWT_EXPIRES_IN") or os.getenv("JWT_EXPIRES_IN", "1h"))

    db = config.get("DATABASE") or make_database(config.get("DATABASE_URL") or database_url())
    app.extensions["services"] = Services(db, secret, expires)
    app.register_blueprint(api)

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"error": {"code": err.code, "message": err.message}}), err.status

    @app.errorhandler(404)
    @app.errorhandler(405)
    def handle_http_error(err):
        if request.path.startswith("/api/"):
            code = "not_found" if err.code == 404 else "method_not_allowed"
            return jsonify({"error": {"code": code, "message": err.name}}), err.code
        return err

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        if hasattr(err, "code") and isinstance(err.code, int):  # errores HTTP de Flask
            return err
        app.logger.exception("Error no controlado")
        return jsonify({"error": {"code": "internal_error", "message": "Error interno del servidor"}}), 500

    return app
