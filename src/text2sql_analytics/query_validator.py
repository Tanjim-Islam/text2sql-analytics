from __future__ import annotations

import re
from typing import Final


BLOCKED_KEYWORDS: Final[tuple[str, ...]] = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "CREATE",
    "ALTER",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "COMMIT",
    "ROLLBACK",
)

BLOCKED_SCHEMAS: Final[tuple[str, ...]] = (
    "pg_catalog",
    "information_schema",
)


def _strip_comments(sql: str) -> str:
    no_block = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    no_line = re.sub(r"--.*?(\n|$)", " ", no_block)
    return no_line


def _is_select_only(sql: str) -> bool:
    s = sql.strip().upper()
    return s.startswith("SELECT") or s.startswith("WITH ")


def _contains_blocked_keywords(sql: str) -> bool:
    up = sql.upper()
    return any(re.search(rf"\b{kw}\b", up) for kw in BLOCKED_KEYWORDS)


def _contains_blocked_schemas(sql: str) -> bool:
    up = sql.upper()
    return any(schema.upper() in up for schema in BLOCKED_SCHEMAS)


def _has_multiple_statements(sql: str) -> bool:
    body = sql.strip().rstrip(";")
    return ";" in body


def _enforce_limit(sql: str, row_limit: int) -> str:
    m = re.search(r"\bLIMIT\s+(\d+)", sql, flags=re.I)
    if m:
        current = int(m.group(1))
        if current > row_limit:
            sql = re.sub(r"\bLIMIT\s+\d+", f"LIMIT {row_limit}", sql, flags=re.I)
        return sql
    return f"{sql.rstrip(';')} LIMIT {row_limit}"


def sanitize_and_validate(sql: str, row_limit: int) -> str:
    sql = _strip_comments(sql)
    if _has_multiple_statements(sql):
        raise ValueError("Multiple statements are not allowed")
    if not _is_select_only(sql):
        raise ValueError("Only SELECT/CTE queries are allowed")
    if _contains_blocked_keywords(sql):
        raise ValueError("Blocked SQL keyword detected")
    if _contains_blocked_schemas(sql):
        raise ValueError("Access to system schemas is not allowed")
    sql = _enforce_limit(sql, row_limit)
    return sql


QueryValidator = sanitize_and_validate

__all__ = [
    "sanitize_and_validate",
    "QueryValidator",
]
