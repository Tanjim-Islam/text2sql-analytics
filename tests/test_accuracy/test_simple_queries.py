from text2sql_analytics.text2sql_engine import Text2SQLEngine
from text2sql_analytics.query_validator import sanitize_and_validate


def test_count_customers_executes():
    # Q: How many customers are there?
    eng = Text2SQLEngine.create()
    eng.use_llm = False
    sql = eng.generate_sql("How many customers are there?", row_limit=1000)
    rows = eng.execute(sql)
    assert isinstance(rows, list)


def test_count_products_not_discontinued():
    # Q: How many products are currently not discontinued?
    eng = Text2SQLEngine.create()
    eng.use_llm = False
    sql = "SELECT COUNT(*) AS cnt FROM products WHERE discontinued = 0"
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert len(rows) == 1


def test_list_customers_from_germany():
    # Q: List all customers from Germany
    eng = Text2SQLEngine.create()
    eng.use_llm = False
    sql = "SELECT customer_id, company_name FROM customers WHERE country = 'Germany'"
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert isinstance(rows, list)


def test_unit_price_of_most_expensive_product():
    # Q: What is the unit price of the most expensive product?
    eng = Text2SQLEngine.create()
    eng.use_llm = False
    sql = "SELECT unit_price FROM products ORDER BY unit_price DESC NULLS LAST LIMIT 1"
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert len(rows) == 1 and 'unit_price' in rows[0]


def test_orders_shipped_in_1997():
    # Q: Show all orders shipped in 1997
    eng = Text2SQLEngine.create()
    eng.use_llm = False
    sql = (
        "SELECT order_id FROM orders "
        "WHERE shipped_date >= DATE '1997-01-01' AND shipped_date < DATE '1998-01-01'"
    )
    sql = sanitize_and_validate(sql, 1000)
    rows = eng.execute(sql)
    assert isinstance(rows, list)
