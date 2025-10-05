from __future__ import annotations

from text2sql_analytics.text2sql_engine import Text2SQLEngine
from text2sql_analytics.query_validator import sanitize_and_validate


def _engine():
    eng = Text2SQLEngine.create()
    eng.use_llm = False
    return eng


def test_monthly_sales_per_category_with_subquery():
    # Q: Year-over-year sales growth per category (monthly breakdown proxy)
    eng = _engine()
    sql = (
        "WITH od AS (SELECT od.order_id, od.product_id, (od.unit_price * od.quantity) AS amount FROM order_details od), "
        "o AS (SELECT order_id, order_date FROM orders) "
        "SELECT date_part('month', o.order_date) AS month, c.category_name, SUM(od.amount) AS sales "
        "FROM od JOIN products p ON od.product_id = p.product_id "
        "JOIN categories c ON p.category_id = c.category_id JOIN o ON o.order_id = od.order_id "
        "GROUP BY month, c.category_name ORDER BY month, c.category_name"
    )
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert isinstance(rows, list)


def test_top_customers_by_spend_with_cte_and_limit():
    # Q: Top customers by total lifetime value (spend)
    eng = _engine()
    sql = (
        "WITH line AS (SELECT order_id, (unit_price * quantity) AS amount FROM order_details), "
        "order_total AS (SELECT order_id, SUM(amount) AS total FROM line GROUP BY order_id) "
        "SELECT o.customer_id, SUM(ot.total) AS spend FROM order_total ot JOIN orders o ON o.order_id = ot.order_id "
        "GROUP BY o.customer_id ORDER BY spend DESC LIMIT 5"
    )
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert len(rows) <= 5


def test_employee_order_counts_with_self_reference():
    # Q: Employee performance — order counts per employee
    eng = _engine()
    sql = (
        "SELECT e.employee_id, e.first_name, e.last_name, COUNT(o.order_id) AS cnt "
        "FROM employees e LEFT JOIN orders o ON e.employee_id = o.employee_id "
        "GROUP BY e.employee_id, e.first_name, e.last_name ORDER BY cnt DESC"
    )
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert isinstance(rows, list)


def test_low_stock_products_with_orders():
    # Q: Products with low stock (operational insight)
    eng = _engine()
    sql = (
        "SELECT p.product_id, p.product_name, p.units_in_stock FROM products p "
        "WHERE p.units_in_stock IS NOT NULL AND p.units_in_stock < 10"
    )
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert isinstance(rows, list)


def test_orders_without_details():
    # Q: Orders without line items (data quality)
    eng = _engine()
    sql = (
        "SELECT o.order_id FROM orders o "
        "WHERE NOT EXISTS (SELECT 1 FROM order_details od WHERE od.order_id = o.order_id)"
    )
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert isinstance(rows, list)


