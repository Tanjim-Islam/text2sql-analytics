import pytest

from text2sql_analytics.query_validator import sanitize_and_validate


def test_allow_select_and_enforce_limit():
    out = sanitize_and_validate("select * from customers", row_limit=1000)
    assert "LIMIT 1000" in out.upper()


@pytest.mark.parametrize(
    "sql",
    [
        "insert into x values (1)",
        "drop table x",
        "update x set a=1",
    ],
)
def test_block_mutations(sql):
    with pytest.raises(ValueError):
        sanitize_and_validate(sql, row_limit=1000)


def test_block_system_schemas():
    with pytest.raises(ValueError):
        sanitize_and_validate("select * from pg_catalog.pg_tables", row_limit=1000)


def test_block_multiple_statements():
    with pytest.raises(ValueError):
        sanitize_and_validate("select 1; select 2", row_limit=1000)
