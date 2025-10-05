from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Connection

from .config import get_settings


@dataclass
class Database:
    engine: Engine

    @classmethod
    def from_env(cls) -> "Database":
        settings = get_settings()
        connect_args = {
            "options": f"-c statement_timeout={(settings.query_timeout_seconds*1000)}"
        }
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            connect_args=connect_args,
        )
        return cls(engine=engine)

    @contextmanager
    def connect(self) -> Iterator[Connection]:
        conn = self.engine.connect()
        try:
            yield conn
        finally:
            conn.close()

    def select_one(self) -> Any:
        with self.connect() as conn:
            result = conn.execute(text("SELECT 1 AS ok"))
            row = result.first()
            return row[0] if row else None
