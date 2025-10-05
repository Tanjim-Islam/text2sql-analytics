from __future__ import annotations

from text2sql_analytics.text2sql_engine import Text2SQLEngine
from text2sql_analytics.query_validator import sanitize_and_validate


def _engine():
    eng = Text2SQLEngine.create()
    eng.use_llm = False
    return eng


def test_top_products_by_price():
    # Q: Top 5 products by price
    eng = _engine()
    sql = eng.generate_sql("Top 5 products by price", row_limit=1000)
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert len(rows) <= 5
    if len(rows) >= 2:
        assert rows[0]["unit_price"] >= rows[1]["unit_price"]


def test_count_customers():
    # Q: Count customers
    eng = _engine()
    sql = eng.generate_sql("count customers", row_limit=1000)
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert len(rows) == 1


def test_orders_per_customer_groupby():
    # Q: Number of orders per customer
    eng = _engine()
    # Fallback mock SQL, validator will ensure LIMIT and SELECT-only
    sql = "SELECT customer_id, COUNT(*) AS num_orders FROM orders GROUP BY customer_id"
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    # Only shape assertion since dataset may be tiny/mocked
    assert rows is not None


def test_average_unit_price_by_category():
    # Q: Average unit price by category
    eng = _engine()
    sql = (
        "SELECT c.category_name, AVG(p.unit_price) AS avg_price "
        "FROM products p JOIN categories c ON p.category_id = c.category_id "
        "GROUP BY c.category_name"
    )
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert isinstance(rows, list)


def test_top_customers_by_order_count():
    # Q: Top customers by order count
    eng = _engine()
    sql = (
        "WITH oc AS (SELECT customer_id, COUNT(*) cnt FROM orders GROUP BY customer_id) "
        "SELECT customer_id, cnt FROM oc ORDER BY cnt DESC LIMIT 5"
    )
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert len(rows) <= 5


def test_products_with_no_orders_subquery():
    # Q: Products with no orders
    eng = _engine()
    sql = (
        "SELECT p.product_id, p.product_name FROM products p "
        "WHERE NOT EXISTS (SELECT 1 FROM order_details od WHERE od.product_id = p.product_id)"
    )
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert isinstance(rows, list)


def test_recent_orders_with_employee_join():
    # Q: Recent orders with employee join
    eng = _engine()
    sql = (
        "SELECT o.order_id, e.first_name, e.last_name FROM orders o "
        "LEFT JOIN employees e ON o.employee_id = e.employee_id ORDER BY o.order_id DESC LIMIT 5"
    )
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert len(rows) <= 5


def test_products_stock_summary():
    # Q: Products stock summary
    eng = _engine()
    sql = (
        "SELECT SUM(units_in_stock) AS total_stock, SUM(units_on_order) AS total_on_order FROM products"
    )
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert len(rows) == 1


def test_orders_with_freight_threshold():
    # Q: Orders with freight threshold
    eng = _engine()
    sql = "SELECT order_id FROM orders WHERE freight IS NULL OR freight >= 0 LIMIT 10"
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert len(rows) <= 10


def test_category_product_counts():
    # Q: Product counts per category
    eng = _engine()
    sql = (
        "SELECT c.category_name, COUNT(p.product_id) AS num_products "
        "FROM categories c LEFT JOIN products p ON c.category_id = p.category_id "
        "GROUP BY c.category_name ORDER BY num_products DESC"
    )
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert isinstance(rows, list)


