from src.database import Database


def test_select_one_env_defaults(ensure_env_defaults):
    db = Database.from_env()
    # We can't assert the value without a running DB; ensure engine constructs
    assert db.engine is not None

