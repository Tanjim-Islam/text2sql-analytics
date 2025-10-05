import os
import pytest


@pytest.fixture(scope="session", autouse=False)
def ensure_env_defaults(tmp_path_factory):
    os.environ.setdefault("DB_HOST", "localhost")
    os.environ.setdefault("DB_PORT", "5432")
    os.environ.setdefault("DB_NAME", "northwind")
    os.environ.setdefault("DB_USER_RO", "ro")
    os.environ.setdefault("DB_PASS_RO", "changeme")
    os.environ.setdefault("QUERY_TIMEOUT_SECONDS", "5")
    os.environ.setdefault("ROW_LIMIT", "1000")
    yield

