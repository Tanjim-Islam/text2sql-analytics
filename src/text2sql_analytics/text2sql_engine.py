from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .config import get_settings
from .database import Database
from .query_validator import sanitize_and_validate

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None  # type: ignore


SYSTEM_PROMPT = (
    "You translate user questions into safe, efficient PostgreSQL SELECT queries. "
    "Only generate one SELECT statement with optional CTEs, never modify data."
)


@dataclass
class Text2SQLEngine:
    db: Database
    use_llm: bool = True

    @classmethod
    def create(cls) -> "Text2SQLEngine":
        db = Database.from_env()
        return cls(db=db, use_llm=True)

    def _init_llm(self) -> Optional[Any]:
        settings = get_settings()
        api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        model = settings.gemini_model or os.getenv("GEMINI_MODEL") or "gemini-2.5-pro"
        if not api_key or genai is None:
            return None
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(model)

    def _mock_generate(self, question: str) -> str:
        q = question.lower()
        if "customer" in q and "count" in q:
            return "SELECT COUNT(*) FROM customers"
        if "top" in q and "product" in q:
            return "SELECT product_name, unit_price FROM products ORDER BY unit_price DESC LIMIT 5"
        return "SELECT 1"

    def generate_sql(self, question: str, row_limit: int) -> str:
        model = self._init_llm() if self.use_llm else None
        if model is None:
            return sanitize_and_validate(self._mock_generate(question), row_limit)
        prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {question}\nSQL:"
        resp = model.generate_content(prompt)
        sql = resp.text if hasattr(resp, "text") else str(resp)
        return sanitize_and_validate(sql, row_limit)

    def execute(self, sql: str) -> List[Dict[str, Any]]:
        from sqlalchemy import text as sqla_text

        with self.db.connect() as conn:
            rows = conn.execute(sqla_text(sql))
            cols = rows.keys()
            return [dict(zip(cols, r)) for r in rows]
