from __future__ import annotations

from text2sql_analytics.text2sql_engine import Text2SQLEngine
from text2sql_analytics.query_validator import sanitize_and_validate
from text2sql_analytics.config import get_settings


def test_cache_metrics_and_hits():
    eng = Text2SQLEngine.create()
    eng.use_llm = False
    q = "count customers"
    r1 = eng.ask(q)
    assert r1["cached"] is False
    r2 = eng.ask(q)
    assert r2["cached"] is True
    m = eng.cache_metrics()
    assert m["cache_hits"] >= 1 and m["cache_misses"] >= 1


def test_explain_generates_tips_or_is_disabled():
    eng = Text2SQLEngine.create()
    eng.use_llm = False
    settings = get_settings()
    sql = sanitize_and_validate("SELECT 1", settings.row_limit)
    out = eng.explain(sql)
    assert isinstance(out, dict)

