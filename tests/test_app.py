import pytest

from app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json()["service"] == "ci-lab-1"


def test_list_items_empty(client):
    response = client.get("/items")
    assert response.status_code == 200
    assert response.get_json() == {"items": [], "count": 0}


def test_create_item(client):
    response = client.post("/items", json={"name": "keyboard"})
    assert response.status_code == 201
    assert response.get_json() == {"id": 1, "name": "keyboard"}


def test_create_item_requires_name(client):
    response = client.post("/items", json={})
    assert response.status_code == 400
    assert response.get_json() == {"error": "name is required"}


def test_list_items_after_create(client):
    client.post("/items", json={"name": "mouse"})
    response = client.get("/items")
    body = response.get_json()
    assert body["count"] == 1
    assert body["items"][0]["name"] == "mouse"
