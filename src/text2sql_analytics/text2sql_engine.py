from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
import time

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
    _cache: Dict[str, Tuple[float, Dict[str, Any]]] = field(default_factory=dict)
    _cache_hits: int = 0
    _cache_misses: int = 0

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

    def _schema_signature(self) -> str:
        from sqlalchemy import text as sqla_text

        with self.db.connect() as conn:
            rows = conn.execute(
                sqla_text(
                    """
                    SELECT table_name, column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position
                    """
                )
            ).all()
        payload = {"schema": rows}
        return hashlib.sha256(json.dumps(payload, default=str).encode()).hexdigest()

    @staticmethod
    def _normalize_prompt(question: str) -> str:
        return " ".join(question.lower().strip().split())

    def _cache_key(self, question: str) -> str:
        key_src = {
            "prompt": self._normalize_prompt(question),
            "schema": self._schema_signature(),
        }
        return hashlib.sha256(json.dumps(key_src).encode()).hexdigest()

    def execute(self, sql: str) -> List[Dict[str, Any]]:
        from sqlalchemy import text as sqla_text

        with self.db.connect() as conn:
            rows = conn.execute(sqla_text(sql))
            cols = rows.keys()
            return [dict(zip(cols, r)) for r in rows]

    def ask(self, question: str, row_limit: Optional[int] = None) -> Dict[str, Any]:
        settings = get_settings()
        ttl = settings.cache_ttl_seconds
        limit = row_limit or settings.row_limit

        cache_key = self._cache_key(question)
        now = time.time()
        entry = self._cache.get(cache_key)
        if entry and (now - entry[0] <= ttl):
            self._cache_hits += 1
            return {**entry[1], "cached": True}

        sql = self.generate_sql(question, row_limit=limit)
        rows = self.execute(sql)
        result = {"sql": sql, "rows": rows, "columns": list(rows[0].keys()) if rows else []}
        self._cache[cache_key] = (now, result)
        self._cache_misses += 1
        return {**result, "cached": False}

    def cache_metrics(self) -> Dict[str, int]:
        return {"cache_hits": self._cache_hits, "cache_misses": self._cache_misses}

    def explain(self, sql: str) -> Dict[str, Any]:
        settings = get_settings()
        if not settings.enable_explain:
            return {"enabled": False}
        from sqlalchemy import text as sqla_text

        with self.db.connect() as conn:
            plan = conn.execute(
                sqla_text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql)
            ).scalar_one()
        plan_json = plan[0] if isinstance(plan, list) else plan
        return {"plan": plan_json, "tips": self._generate_tips(plan_json)}

    @staticmethod
    def _generate_tips(plan_json: Any) -> List[str]:
        tips: List[str] = []
        try:
            root = plan_json[0]["Plan"] if isinstance(plan_json, list) else plan_json["Plan"]
            exec_time = plan_json[0].get("Execution Time") if isinstance(plan_json, list) else plan_json.get("Execution Time")
            if exec_time and exec_time > 1000.0:
                tips.append("Execution time high; consider additional indexes or filters")
            node_type = root.get("Node Type", "")
            if node_type == "Seq Scan":
                tips.append("Sequential scan detected; consider an index on filter/join columns")
            if root.get("Join Type") == "Nested Loop" and root.get("Plan Rows", 0) > 10000:
                tips.append("Nested Loop on large rows; ensure indexes exist on join keys")
        except Exception:
            tips.append("Could not parse EXPLAIN JSON")
        return tips
