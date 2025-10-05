from __future__ import annotations

import os
import sys
from typing import Iterable

import psycopg
from dotenv import load_dotenv


ADMIN_USER = os.getenv("DB_USER_ADMIN", "admin")
ADMIN_PASS = os.getenv("DB_PASS_ADMIN", "changeme")
DB_NAME = os.getenv("DB_NAME", "northwind")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))

READ_ONLY_USER = os.getenv("DB_USER_RO", "ro")
READ_ONLY_PASS = os.getenv("DB_PASS_RO", "changeme")


DDL_STATEMENTS: Iterable[str] = [

    """
    CREATE TABLE IF NOT EXISTS healthcheck (
        id SERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """,
]


ROLE_STATEMENTS: Iterable[str] = [
    f"CREATE ROLE {READ_ONLY_USER} LOGIN PASSWORD '{READ_ONLY_PASS}';",
    f"ALTER ROLE {READ_ONLY_USER} WITH PASSWORD '{READ_ONLY_PASS}';",
    f"REVOKE ALL ON SCHEMA public FROM {READ_ONLY_USER};",
    f"GRANT USAGE ON SCHEMA public TO {READ_ONLY_USER};",
    f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {READ_ONLY_USER};",
    f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {READ_ONLY_USER};",
]


BLOCK_MUTATIONS: Iterable[str] = [
    f"REVOKE CREATE ON SCHEMA public FROM {READ_ONLY_USER};",
    f"GRANT CONNECT ON DATABASE {DB_NAME} TO {READ_ONLY_USER};",
]


def main() -> int:
    load_dotenv()
    try:
        with psycopg.connect(
            dbname=DB_NAME,
            user=ADMIN_USER,
            password=ADMIN_PASS,
            host=DB_HOST,
            port=DB_PORT,
            autocommit=True,
        ) as conn:
            with conn.cursor() as cur:
                for ddl in DDL_STATEMENTS:
                    cur.execute(ddl)
                schema_path = os.path.join(os.path.dirname(__file__), "..", "data", "schema", "schema.sql")
                schema_path = os.path.abspath(schema_path)
                if os.path.exists(schema_path):
                    with open(schema_path, "r", encoding="utf-8") as f:
                        sql = f.read()
                    for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
                        try:
                            cur.execute(stmt)
                        except Exception:
                            conn.rollback()
                for stmt in ROLE_STATEMENTS:
                    try:
                        cur.execute(stmt)
                    except Exception:
                        conn.rollback()
                for stmt in BLOCK_MUTATIONS:
                    cur.execute(stmt)
        print("[setup_database] schema and roles prepared")
    except Exception as exc:  # noqa: BLE001
        print(f"[setup_database] connection failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

