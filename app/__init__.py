"""Минимальное Flask-приложение — база для лабораторной работы по CI.

Сложность приложения не оценивается: важно то, что происходит
вокруг него в Pipeline (lint, тесты с покрытием, сборка).
"""
from flask import Flask, jsonify, request

from app import reports


def create_app():
    """Фабрика приложения."""
    app = Flask(__name__)
    app.config["ITEMS"] = {}

    @app.route("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.route("/")
    def index():
        return jsonify(service="ci-lab-1", status="running"), 200

    @app.route("/items", methods=["GET"])
    def list_items():
        items = list(app.config["ITEMS"].values())
        return jsonify(items=items, count=len(items)), 200

    @app.route("/items", methods=["POST"])
    def create_item():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify(error="name is required"), 400

        item_id = max(app.config["ITEMS"], default=0) + 1
        item = {"id": item_id, "name": name}
        app.config["ITEMS"][item_id] = item
        return jsonify(item), 201

    # --- ЭКСПЕРИМЕНТ (раздел 5.7): новый маршрут, тестов к нему нет ---
    @app.route("/reports", methods=["GET"])
    def reports_route():
        items = list(app.config["ITEMS"].values())
        data = reports.summarize(items)
        data["starting_with_k"] = len(reports.filter_by_prefix(items, "k"))
        return jsonify(data), 200

    return app
