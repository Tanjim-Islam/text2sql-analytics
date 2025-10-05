from text2sql_analytics.text2sql_engine import Text2SQLEngine


def test_mock_generation_and_validation():
    eng = Text2SQLEngine.create()
    eng.use_llm = False
    sql = eng.generate_sql("count customers", row_limit=1000)
    assert "SELECT" in sql.upper()
    assert "LIMIT" in sql.upper() or "COUNT(" in sql.upper()
