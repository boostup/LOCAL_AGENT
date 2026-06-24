import abc
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any


DATA_DIR = Path(os.environ.get("LOCAL_AI_DATA_DIR", "data"))
DB_PATH = Path(os.environ.get("LOCAL_AI_DB_PATH", DATA_DIR / "agent.sqlite"))


class Skill(abc.ABC):
    name = "base"
    trigger_words: tuple[str, ...] = ()
    cache_ttl = 3600

    async def execute_with_context(self, query: str = "", **kwargs: Any) -> str:
        started = time.perf_counter()
        cache_key = self.cache_key(query, kwargs)
        cached = self.get_cached(cache_key)
        if cached is not None:
            self.record_metric(time.perf_counter() - started, True, True)
            return cached
        try:
            response = await self.execute(query, **kwargs)
            if response:
                self.set_cached(cache_key, response)
            self.record_metric(time.perf_counter() - started, True, False)
            return response
        except Exception as exc:
            self.record_metric(time.perf_counter() - started, False, False, str(exc))
            return f"{self.name.title()} is unavailable: {exc}"

    @abc.abstractmethod
    async def execute(self, query: str = "", **kwargs: Any) -> str:
        raise NotImplementedError

    def matches(self, message: str) -> bool:
        lowered = message.lower()
        return any(trigger in lowered for trigger in self.trigger_words)

    def cache_key(self, query: str, kwargs: dict[str, Any]) -> str:
        payload = json.dumps({"skill": self.name, "query": query, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def connection(self) -> sqlite3.Connection:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.execute("create table if not exists cache (key text primary key, skill text not null, value text not null, expires_at real not null)")
        conn.execute("create table if not exists metrics (id integer primary key autoincrement, skill text not null, duration real not null, success integer not null, cache_hit integer not null, error text, created_at real not null)")
        conn.execute("create table if not exists feedback (id integer primary key autoincrement, text text not null, created_at real not null)")
        return conn

    def get_cached(self, key: str) -> str | None:
        with self.connection() as conn:
            row = conn.execute("select value from cache where key = ? and expires_at > ?", (key, time.time())).fetchone()
            if row:
                return str(row[0])
            conn.execute("delete from cache where key = ?", (key,))
        return None

    def set_cached(self, key: str, value: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "insert or replace into cache (key, skill, value, expires_at) values (?, ?, ?, ?)",
                (key, self.name, value, time.time() + self.cache_ttl),
            )

    def record_metric(self, duration: float, success: bool, cache_hit: bool, error: str | None = None) -> None:
        with self.connection() as conn:
            conn.execute(
                "insert into metrics (skill, duration, success, cache_hit, error, created_at) values (?, ?, ?, ?, ?, ?)",
                (self.name, duration, int(success), int(cache_hit), error, time.time()),
            )
