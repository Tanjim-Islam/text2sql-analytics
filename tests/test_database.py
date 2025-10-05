from text2sql_analytics.database import Database


def test_select_one_env_defaults(ensure_env_defaults):
    db = Database.from_env()
    assert db.engine is not None
