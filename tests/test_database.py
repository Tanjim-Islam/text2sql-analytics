from text2sql_analytics.database import Database
from text2sql_analytics.text2sql_engine import Text2SQLEngine


def test_select_one_env_defaults(ensure_env_defaults):
    db = Database.from_env()
    assert db.engine is not None


def test_engine_execute_and_cache_metrics(ensure_env_defaults):
    eng = Text2SQLEngine.create()
    eng.use_llm = False
    res1 = eng.ask("count customers")
    assert res1["cached"] is False
    res2 = eng.ask("count customers")
    assert res2["cached"] is True
