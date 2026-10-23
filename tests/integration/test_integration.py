"""Интеграционные тесты с реальными PostgreSQL и Redis (Testcontainers)."""
import psycopg
import pytest
import redis


def test_ready_reports_real_dependencies(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ready", "storage": "postgres+redis"}


def test_empty_list(client):
    response = client.get("/items")
    assert response.status_code == 200
    assert response.get_json() == {"items": [], "count": 0}


def test_create_item_persists_in_postgres(client, env):
    response = client.post("/items", json={"name": "keyboard"})
    assert response.status_code == 201
    assert response.get_json() == {"id": 1, "name": "keyboard"}

    dsn, _ = env
    with psycopg.connect(dsn) as conn:
        rows = conn.execute("SELECT id, name FROM items").fetchall()

    assert rows == [(1, "keyboard")]


def test_get_items_uses_cache(client, env):
    client.post("/items", json={"name": "mouse"})

    first = client.get("/items")
    second = client.get("/items")

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert second.get_json()["count"] == 1

    _, redis_url = env
    cache = redis.Redis.from_url(redis_url, decode_responses=True)
    assert cache.exists("items:all") == 1


def test_create_invalidates_cache(client):
    client.post("/items", json={"name": "one"})
    client.get("/items")

    client.post("/items", json={"name": "two"})
    response = client.get("/items")

    assert response.headers["X-Cache"] == "MISS"
    assert response.get_json()["count"] == 2


def test_create_requires_name(client):
    response = client.post("/items", json={})
    assert response.status_code == 400
    assert response.get_json() == {"error": "name is required"}


def test_redis_contains_cached_payload(client, env):
    client.post("/items", json={"name": "cached"})
    client.get("/items")

    _, redis_url = env
    cache = redis.Redis.from_url(redis_url, decode_responses=True)
    payload = cache.get("items:all")

    assert payload is not None
    assert "cached" in payload


@pytest.mark.parametrize("index", range(12))
def test_create_many_items(client, index):
    for number in range(20):
        response = client.post("/items", json={"name": f"item-{index}-{number}"})
        assert response.status_code == 500  # EXPERIMENT: wrong expectation

    listed = client.get("/items")
    assert listed.get_json()["count"] == 20
