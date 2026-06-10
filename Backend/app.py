from __future__ import annotations

import importlib
from pathlib import Path

from flask import Flask, send_from_directory
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "Frontend"

try:
    load_dotenv = importlib.import_module("dotenv").load_dotenv
except ImportError:  # pragma: no cover - optional during bootstrap
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(BASE_DIR.parent / ".env")

from Backend.routes.api import api_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)
    app.config["JSON_SORT_KEYS"] = False

    app.register_blueprint(api_bp, url_prefix="/api")

    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/<path:filename>")
    def frontend_files(filename: str):
        candidate = FRONTEND_DIR / filename
        if candidate.is_file():
            return send_from_directory(FRONTEND_DIR, filename)
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    import os

    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)