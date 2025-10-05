from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from text2sql_analytics.text2sql_engine import Text2SQLEngine


@dataclass
class QA:
    question: str
    validator: str


def main() -> int:
    eng = Text2SQLEngine.create()
    eng.use_llm = False

    questions: List[str] = [
        "How many customers are there?",
        "List top 5 products by price",
    ]

    for q in questions:
        sql = eng.generate_sql(q, row_limit=1000)
        rows = eng.execute(sql)
        print({"question": q, "sql": sql, "rows": len(rows)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

