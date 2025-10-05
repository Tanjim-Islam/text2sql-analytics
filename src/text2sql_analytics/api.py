from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from datetime import datetime
import time
from pydantic import BaseModel

from .text2sql_engine import Text2SQLEngine
from .query_validator import sanitize_and_validate
from .config import get_settings


app = FastAPI()
engine = Text2SQLEngine.create()
engine.use_llm = False

_STARTED_AT = time.time()


def _uptime_hms() -> str:
    seconds = int(time.time() - _STARTED_AT)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class QueryIn(BaseModel):
    question: str | None = None
    sql: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict:
    m = engine.cache_metrics()
    return {"cache_hits": m["cache_hits"], "cache_misses": m["cache_misses"], "total_queries": m["cache_hits"] + m["cache_misses"]}


@app.post("/query")
def query(body: QueryIn) -> dict:
    if not body.question:
        raise HTTPException(status_code=400, detail="question is required")
    settings = get_settings()
    res = engine.ask(body.question, row_limit=settings.row_limit)
    return res


@app.post("/explain")
def explain(body: QueryIn) -> dict:
    settings = get_settings()
    if not settings.enable_explain:
        raise HTTPException(status_code=400, detail="EXPLAIN disabled")
    if body.sql:
        sql = sanitize_and_validate(body.sql, settings.row_limit)
    elif body.question:
        sql = engine.generate_sql(body.question, row_limit=settings.row_limit)
    else:
        raise HTTPException(status_code=400, detail="provide sql or question")
    return engine.explain(sql)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    m = metrics()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    uptime = _uptime_hms()
    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Text2SQL Dashboard</title>
  <style>
    :root {{ --bg: #f9f1e4; --panel: #f9f1e4; --text: #4a4a4a; --muted: #6a6a6a; --accent: #4a4a4a; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color: var(--text);
           background: var(--bg); }}
    .wrap {{ max-width: 960px; margin: 0 auto; padding: 2rem; }}
    .card {{ background: var(--panel); border-radius: 12px; padding: 1.5rem; box-shadow: 0 6px 24px rgba(74,74,74,0.15); border: 1px solid rgba(74,74,74,0.1); }}
    h1 {{ margin: 0 0 .5rem; font-size: 1.6rem; letter-spacing: .2px; }}
    p.desc {{ margin: 0 0 1rem; color: var(--muted); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); gap: 1rem; margin-top: 1rem; }}
    .kpi {{ background: rgba(74,74,74,0.05); border: 1px solid rgba(74,74,74,0.15); border-radius: 10px; padding: 1rem; }}
    .kpi .label {{ color: var(--muted); font-size: .85rem; }}
    .kpi .value {{ display: block; margin-top: .25rem; font-size: 1.4rem; color: var(--accent); font-weight: 600; }}
    .meta {{ margin-top: 1rem; color: var(--muted); font-size: .9rem; }}
  </style>
  </head>
  <body>
    <main class=\"wrap\">
      <section class=\"card\">
        <h1>Text2SQL Analytics System</h1>
        <p class=\"desc\">Ask a question in natural language, generate a safe SQL SELECT, and return results from the Northwind database. This dashboard shows runtime metrics.</p>
        <div class=\"grid\">
          <div class=\"kpi\"><span class=\"label\">Cache hits</span><span class=\"value\">{m['cache_hits']}</span></div>
          <div class=\"kpi\"><span class=\"label\">Cache misses</span><span class=\"value\">{m['cache_misses']}</span></div>
          <div class=\"kpi\"><span class=\"label\">Total queries</span><span class=\"value\">{m['total_queries']}</span></div>
          <div class=\"kpi\"><span class=\"label\">Uptime</span><span class=\"value\">{uptime}</span></div>
        </div>
        <div class=\"meta\">Updated: {now}</div>
      </section>
    </main>
  </body>
  </html>"""
    return HTMLResponse(content=html, media_type="text/html")


