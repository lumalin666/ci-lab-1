"""Flask-приложение для лабораторных работ по CI/CD.

Базовые маршруты работают и без внешних зависимостей, но если заданы
DATABASE_URL и REDIS_URL, данные хранятся в PostgreSQL, а список
кэшируется в Redis.
"""
import os

from flask import Flask, jsonify, request


def create_app():
    """Фабрика приложения."""
    app = Flask(__name__)
    app.config["ITEMS"] = {}

    database_url = os.getenv("DATABASE_URL")
    redis_url = os.getenv("REDIS_URL")

    storage = None
    if database_url and redis_url:
        from .storage import Storage

        storage = Storage(database_url, redis_url)
        storage.init_schema()

    app.config["STORAGE"] = storage

    @app.route("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.route("/ready")
    def ready():
        if storage is not None:
            storage.check()
            return jsonify(status="ready", storage="postgres+redis"), 200
        return jsonify(status="ready", storage="memory"), 200

    @app.route("/")
    def index():
        return jsonify(service="ci-lab-1", status="running", lab="lab3"), 200

    @app.route("/items", methods=["GET"])
    def list_items():
        if storage is not None:
            items, cached = storage.list_items()
            response = jsonify(items=items, count=len(items))
            response.headers["X-Cache"] = "HIT" if cached else "MISS"
            return response, 200

        items = list(app.config["ITEMS"].values())
        return jsonify(items=items, count=len(items)), 200

    @app.route("/items", methods=["POST"])
    def create_item():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify(error="name is required"), 400

        if storage is not None:
            return jsonify(storage.create_item(name)), 201

        item_id = max(app.config["ITEMS"], default=0) + 1
        item = {"id": item_id, "name": name}
        app.config["ITEMS"][item_id] = item
        return jsonify(item), 201

    return app
