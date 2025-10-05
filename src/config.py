from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    query_timeout_seconds: int
    row_limit: int
    gemini_api_key: str | None
    gemini_model: str | None
    log_level: str


def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL") or (
        f"postgresql+psycopg://{os.getenv('DB_USER_RO','ro')}:{os.getenv('DB_PASS_RO','ro_pass')}@"
        f"{os.getenv('DB_HOST','localhost')}:{os.getenv('DB_PORT','5433')}/{os.getenv('DB_NAME','northwind')}"
    )
    return Settings(
        database_url=database_url,
        query_timeout_seconds=int(os.getenv("QUERY_TIMEOUT_SECONDS", "5")),
        row_limit=int(os.getenv("ROW_LIMIT", "1000")),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

