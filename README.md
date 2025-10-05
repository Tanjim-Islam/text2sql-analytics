# Text2SQL Analytics System

This repository contains the implementation for a production-ready Text2SQL analytics system over the Northwind dataset using PostgreSQL and Google Gemini.

Project overview

- Ask a question in English. The system translates it to safe SQL, runs it on a PostgreSQL version of the Northwind dataset, and returns results.

Architecture (ASCII)

```
[User Question]
     |
     v
[Text2SQL Engine] --(prompts)--> [Gemini API (optional)]
     |                                 |
     | (SQL candidate)                  |
     v                                 v
[SQL Validator] --(sanitized SELECT)-->[PostgreSQL 14]
     |                                       ^
     v                                       |
[Results JSON] <----------------------- [Data Loader + 3NF Schema]
     |
     v
[Evaluation Script] and [Tests]
```

PDF mapping (what section satisfies what)
| README section | PDF section(s) |
| --- | --- |
| Project overview | Objectives and grading rubric |
| Prerequisites | Technology stack and environment |
| Quick start | Repository structure and submission guidelines |
| Configuration | Deliverables and security checklist |
| Database setup | Database layer and Docker guidance |
| Data loading and normalization | Data normalization and database layer |
| Text2SQL engine and safety | Text2SQL engine and security restrictions |
| How to test it | Testing requirements and testing suite |
| Troubleshooting | Tips and FAQ |
| Deliverables checklist | Deliverables and submission guidelines |
| Future work | Bonus items |

Prerequisites

- Python 3.10+, Git.
- Docker Desktop (optional) to run PostgreSQL 14 easily.
- PostgreSQL: either via Docker on port 5433, or a local server on 5432.
- Secrets and credentials go in `.env` (already gitignored). Do not commit real keys.

Quick start

```
# from repo root
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# OR
.\.venv\Scripts\activate  # Windows

pip install -e text2sql-analytics

# Option A: Docker
cd text2sql-analytics
docker compose up -d postgres

# Initialize schema and roles
python scripts/setup_database.py

# Run evaluation (sample Q&A; mock mapping used by default to respect rate limits)
python scripts/run_evaluation.py

# Run tests with coverage report in terminal
python -m pytest -q --cov=src --cov-report=term-missing
```

Use local PostgreSQL instead of Docker

- Ensure a local PostgreSQL runs on 5432, and set in `.env`:
  - `DB_HOST=localhost`, `DB_PORT=5432`, `DB_NAME=postgres`
  - Admin: `DB_USER_ADMIN`, `DB_PASS_ADMIN`
  - Runtime RO: `DB_USER_RO`, `DB_PASS_RO`
- Run the same scripts; they will use your `.env`.

Configuration (environment)

- `DB_HOST`: Database host (e.g., `localhost`).
- `DB_PORT`: Port (`5433` for Docker compose, or `5432` local).
- `DB_NAME`: Database name (`postgres` by default).
- `DB_USER_ADMIN` / `DB_PASS_ADMIN`: Admin role for schema and grants.
- `DB_USER_RO` / `DB_PASS_RO`: Read-only role used by the runtime.
- `GEMINI_API_KEY`: Google Gemini key
- `GEMINI_MODEL`: Model name
- `QUERY_TIMEOUT_SECONDS=5`, `ROW_LIMIT=1000`.

Database setup

- Path A: Docker Compose (5433)
  - `cd text2sql-analytics && docker compose up -d postgres`
  - A named volume persists data. Port 5433 on host maps to 5432 in the container.
- Path B: Local PostgreSQL (5432)
  - Start your server and ensure admin credentials in `.env`.
  - Set `DB_PORT=5432`.
- Initialize schema/roles
  - `python scripts/setup_database.py`
  - Creates/updates a read-only role, grants SELECT, and prepares base tables.
- Verify connections
  - Admin: run `python -c "import os;from text2sql_analytics.database import Database;print(Database.from_env().select_one())"` with admin env.
  - Read-only: set `DB_USER_RO`, `DB_PASS_RO` then run the same; expect `1`.

Data loading and normalization

- Place `northwind.xlsx` at `text2sql-analytics/data/raw/northwind.xlsx`.
- The Data Loader will:
  - Read sheets, coerce types, dedupe, validate FKs.
  - Create normalized (3NF) tables with PKs, FKs, and indexes.
  - If some sheets are missing, deterministic mock data is used to complete the pipeline.
- Run a quick normalization report

```
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# OR
.\.venv\Scripts\activate  # Windows

python - << 'PY'
import os, sys
sys.path.insert(0, 'text2sql-analytics')
from text2sql_analytics.data_loader import DataLoader, LoaderConfig
cfg = LoaderConfig(
  db_host=os.getenv('DB_HOST','localhost'),
  db_port=int(os.getenv('DB_PORT','5433')),
  db_name=os.getenv('DB_NAME','postgres'),
  db_user=os.getenv('DB_USER_ADMIN','postgres'),
  db_pass=os.getenv('DB_PASS_ADMIN','changeme'),
)
dl = DataLoader(cfg)
print(dl.generate_report())
PY
```

Text2SQL engine and safety rules

- Prompt context: brief instruction, safety policy; optional Gemini model.
- Validator enforces:
  - SELECT/CTE only (no INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/TRUNCATE/GRANT/REVOKE).
  - Single statement only (no `;` chaining), block `pg_catalog` and `information_schema`.
  - LIMIT 1000 added if missing; server `statement_timeout` set to 5s.
- Errors: user-friendly messages; internal logs can include details (no secret leakage).

How to test it

```
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# OR
.\.venv\Scripts\activate  # Windows

cd text2sql-analytics
python -m pytest -q --cov=src --cov-report=term-missing
```

- Accuracy script (mock-based by default): `python scripts/run_evaluation.py`.
- Target coverage: 80%+ (as per PDF). Use `--cov-report=html` for an HTML report.

Troubleshooting

- Password authentication failed
  - Verify `.env` credentials. You can encode passwords in a URI if special chars.
- Port conflicts 5432 vs 5433
  - Switch `DB_PORT` to the one you’re using and ensure docker compose mapping.
- ModuleNotFoundError
  - Run `pip install -e text2sql-analytics`. In ad‑hoc sessions, set `PYTHONPATH=$(pwd)` (macOS/Linux) or `$env:PYTHONPATH=(Get-Location).Path` (Windows).
- Slow queries
  - Confirm sanitized SQL includes `LIMIT`. The server enforces `statement_timeout=5000ms`.

Deliverables checklist (from PDF)

- Working code in `src/`, tests in `tests/` (unit, integration, accuracy), scripts in `scripts/`.
- Documentation (this README) and `EVALUATION.md` with results.
- Coverage report available via pytest-cov.

Future work and bonus items

- Query caching (by normalized prompt + schema signature).
- EXPLAIN/ANALYZE collection and optimization tips.
- REST API (FastAPI) endpoint for programmatic access.
- Lightweight dashboard for performance monitoring.
