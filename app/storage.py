"""Хранилище для ЛР3: PostgreSQL + кэш в Redis.

Если переменные окружения DATABASE_URL и REDIS_URL не заданы,
приложение работает в прежнем in-memory режиме (это нужно для unit-тестов).
"""
import json

import psycopg
import redis


class Storage:
    CACHE_KEY = "items:all"
    CACHE_TTL = 30

    def __init__(self, database_url: str, redis_url: str):
        self.dsn = database_url
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)

    def init_schema(self) -> None:
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL
                )
                """
            )

    def list_items(self) -> tuple[list[dict], bool]:
        cached = self.redis.get(self.CACHE_KEY)
        if cached is not None:
            return json.loads(cached), True

        with psycopg.connect(self.dsn) as conn:
            rows = conn.execute(
                "SELECT id, name FROM items ORDER BY id"
            ).fetchall()

        items = [{"id": row[0], "name": row[1]} for row in rows]
        self.redis.set(self.CACHE_KEY, json.dumps(items), ex=self.CACHE_TTL)
        return items, False

    def create_item(self, name: str) -> dict:
        with psycopg.connect(self.dsn) as conn:
            row = conn.execute(
                "INSERT INTO items (name) VALUES (%s) RETURNING id, name",
                (name,),
            ).fetchone()

        self.redis.delete(self.CACHE_KEY)
        return {"id": row[0], "name": row[1]}

    def check(self) -> None:
        with psycopg.connect(self.dsn) as conn:
            conn.execute("SELECT 1")
        self.redis.ping()
