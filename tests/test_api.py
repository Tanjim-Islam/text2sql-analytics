from __future__ import annotations

from fastapi.testclient import TestClient

from text2sql_analytics.api import app


def test_health_and_metrics():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    r2 = client.get("/metrics")
    assert r2.status_code == 200
    data = r2.json()
    assert "cache_hits" in data and "cache_misses" in data


def test_query_endpoint_and_cache():
    client = TestClient(app)
    payload = {"question": "count customers"}
    r1 = client.post("/query", json=payload)
    assert r1.status_code == 200
    d1 = r1.json()
    assert "sql" in d1 and "rows" in d1 and d1.get("cached") is False
    r2 = client.post("/query", json=payload)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2.get("cached") is True


def test_explain_endpoint_and_dashboard():
    client = TestClient(app)
    r = client.post("/explain", json={"question": "count customers"})
    assert r.status_code in (200, 400)
    d = client.get("/dashboard")
    assert d.status_code == 200
    assert d.headers.get("content-type", "").startswith("text/html")
    assert "Text2SQL Analytics System" in d.text


