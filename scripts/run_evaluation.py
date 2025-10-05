from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple
import time
import statistics

from text2sql_analytics.text2sql_engine import Text2SQLEngine
from text2sql_analytics.query_validator import sanitize_and_validate
from text2sql_analytics.config import get_settings


@dataclass
class QA:
    question: str
    category: str  # simple | intermediate | complex
    validator: Callable[[List[Dict[str, object]]], bool]


def _len_at_most(n: int) -> Callable[[List[Dict[str, object]]], bool]:
    return lambda rows: len(rows) <= n


def _has_columns(*names: str) -> Callable[[List[Dict[str, object]]], bool]:
    expected = set(n.lower() for n in names)

    def _check(rows: List[Dict[str, object]]) -> bool:
        if not rows:
            return True
        return expected.issubset(set(str(k).lower() for k in rows[0].keys()))

    return _check


def _single_row() -> Callable[[List[Dict[str, object]]], bool]:
    return lambda rows: len(rows) == 1


def _quality_metrics(sql: str, elapsed_ms: float) -> Dict[str, int]:
    up = sql.upper()
    metrics: Dict[str, int] = {
        "uses_proper_joins": 1 if (" JOIN " in up or " WITH " in up) else 0,
        "has_necessary_where": 1 if (" WHERE " in up or " LIMIT " in up) else 0,
        "correct_group_by": 1 if (" GROUP BY " in up) else 0,
        "efficient_indexing": 1 if any(k in up for k in ["ORDER_DATE", "CUSTOMER_ID", "EMPLOYEE_ID", "PRODUCT_ID"]) else 0,
        "execution_time": 1 if elapsed_ms < 1000.0 else 0,
    }
    return metrics


def run() -> Tuple[float, Dict[str, float]]:
    eng = Text2SQLEngine.create()
    eng.use_llm = False
    settings = get_settings()

    qas: List[QA] = [
        # Simple (5)
        QA("How many customers are there?", "simple", _single_row()),
        QA("List all customers from Germany", "simple", _has_columns("customer_id", "company_name")),
        QA("What is the unit price of the most expensive product?", "simple", _single_row()),
        QA("Show all orders shipped in 1997", "simple", _has_columns("order_id")),
        QA("Which employee has the job title 'Sales Representative'?", "simple", _has_columns("employee_id")),
        # Intermediate (10)
        QA("Top 5 products by price", "intermediate", _len_at_most(5)),
        QA("Count customers", "intermediate", _single_row()),
        QA("Number of orders per customer", "intermediate", _has_columns("customer_id", "num_orders")),
        QA("Average unit price by category", "intermediate", _has_columns("category_name", "avg_price")),
        QA("Top customers by order count", "intermediate", _len_at_most(5)),
        QA("Products with no orders", "intermediate", _has_columns("product_id", "product_name")),
        QA("Recent orders with employee join", "intermediate", _has_columns("order_id")),
        QA("Products stock summary", "intermediate", _single_row()),
        QA("Orders with freight threshold", "intermediate", _len_at_most(10)),
        QA("Product counts per category", "intermediate", _has_columns("category_name", "num_products")),
        # Complex (5)
        QA("Monthly sales per category (YoY proxy)", "complex", _has_columns("month", "category_name", "sales")),
        QA("Top customers by total lifetime value", "complex", _len_at_most(5)),
        QA("Employee performance — order counts", "complex", _has_columns("employee_id", "cnt")),
        QA("Products with low stock", "complex", _has_columns("product_id", "product_name")),
        QA("Orders without line items", "complex", _has_columns("order_id")),
    ]

    per_category: Dict[str, List[float]] = {"simple": [], "intermediate": [], "complex": []}
    exec_successes = 0

    for qa in qas:
        start = time.time()
        try:
            sql = eng.generate_sql(qa.question, row_limit=settings.row_limit)
            # Ensure sanitized and limited
            sql = sanitize_and_validate(sql, settings.row_limit)
            rows = eng.execute(sql)
            execution_success = 1
        except Exception:
            sql = "SELECT 1 LIMIT 1"
            rows = []
            execution_success = 0
        elapsed_ms = (time.time() - start) * 1000.0

        exec_successes += execution_success
        result_match = 1 if execution_success and qa.validator(rows) else 0
        qm = _quality_metrics(sql, elapsed_ms)
        query_quality = statistics.mean(qm.values()) if qm else 0.0

        score = 0.20 * execution_success + 0.40 * result_match + 0.40 * query_quality
        per_category[qa.category].append(score)

        print({
            "category": qa.category,
            "question": qa.question,
            "sql": sql,
            "execution_success": execution_success,
            "result_match": result_match,
            "query_quality": round(query_quality, 3),
            "elapsed_ms": int(elapsed_ms),
            "score": round(score, 3),
        })

    cat_scores = {k: (sum(v) / len(v) if v else 0.0) for k, v in per_category.items()}
    overall = sum(sum(v) for v in per_category.values()) / sum(len(v) for v in per_category.values())
    print({"summary": {**{f"category_{k}": round(s, 3) for k, s in cat_scores.items()}, "overall": round(overall, 3)}})
    return overall, cat_scores


def main() -> int:
    _overall, _cats = run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

