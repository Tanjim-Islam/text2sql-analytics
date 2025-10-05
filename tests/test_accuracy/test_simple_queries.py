from src.text2sql_engine import Text2SQLEngine


def test_count_customers_executes():
    eng = Text2SQLEngine.create()
    eng.use_llm = False
    sql = eng.generate_sql("How many customers are there?", row_limit=1000)
    rows = eng.execute(sql)
    assert isinstance(rows, list)
