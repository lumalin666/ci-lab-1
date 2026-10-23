import json
import os
import tempfile
import time
from pathlib import Path

import psycopg
import pytest
import redis
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer

STATE_FILE = Path(tempfile.gettempdir()) / "ci_lab3_testcontainers.json"


def _state_from_containers(postgres, redis_server):
    return {
        "pg_host": postgres.get_container_host_ip(),
        "pg_port": postgres.get_exposed_port(5432),
        "pg_user": postgres.username,
        "pg_password": postgres.password,
        "pg_db": postgres.dbname,
        "redis_host": redis_server.get_container_host_ip(),
        "redis_port": redis_server.get_exposed_port(6379),
    }


def _connection_urls(state, suffix):
    base = (
        f"host={state['pg_host']} port={state['pg_port']} "
        f"user={state['pg_user']} password={state['pg_password']}"
    )
    database = state["pg_db"] if not suffix else f"lab3_w{suffix}"
    dsn = f"{base} dbname={database}"
    redis_db = int(suffix) if suffix else 0
    redis_url = f"redis://{state['redis_host']}:{state['redis_port']}/{redis_db}"
    return dsn, redis_url, database


def _ensure_database(state, database):
    if database == state["pg_db"]:
        return
    admin_dsn = (
        f"host={state['pg_host']} port={state['pg_port']} "
        f"user={state['pg_user']} password={state['pg_password']} "
        f"dbname={state['pg_db']}"
    )
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (database,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{database}"')


def pytest_configure(config):
    """Поднимает один набор контейнеров и изолирует worker-ы по базам.

    Master-процесс стартует PostgreSQL и Redis через Testcontainers.
    Каждый worker pytest-xdist получает собственную базу PostgreSQL
    и отдельный номер базы Redis, поэтому тесты не мешают друг другу.
    """
    if not hasattr(config, "workerinput"):
        postgres = PostgresContainer("postgres:16-alpine")
        postgres.start()
        redis_server = RedisContainer("redis:7-alpine")
        redis_server.start()

        config._lab3_postgres = postgres
        config._lab3_redis = redis_server

        state = _state_from_containers(postgres, redis_server)
        STATE_FILE.write_text(json.dumps(state), encoding="utf-8")

        dsn, redis_url, _ = _connection_urls(state, "")
        os.environ["DATABASE_URL"] = dsn
        os.environ["REDIS_URL"] = redis_url
    else:
        for _ in range(240):
            if STATE_FILE.exists():
                break
            time.sleep(0.25)

        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        worker_id = config.workerinput.get("workerid", "gw0")
        suffix = "".join(ch for ch in worker_id if ch.isdigit()) or "0"

        dsn, redis_url, database = _connection_urls(state, suffix)
        _ensure_database(state, database)

        os.environ["DATABASE_URL"] = dsn
        os.environ["REDIS_URL"] = redis_url


def pytest_unconfigure(config):
    if not hasattr(config, "workerinput"):
        postgres = getattr(config, "_lab3_postgres", None)
        redis_server = getattr(config, "_lab3_redis", None)
        if postgres is not None:
            postgres.stop()
        if redis_server is not None:
            redis_server.stop()
        STATE_FILE.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def env():
    return os.environ["DATABASE_URL"], os.environ["REDIS_URL"]


@pytest.fixture()
def client(env):
    dsn, redis_url = env

    from app import create_app

    app = create_app()
    app.config["TESTING"] = True

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE items RESTART IDENTITY")

    redis.Redis.from_url(redis_url).flushdb()

    yield app.test_client()
