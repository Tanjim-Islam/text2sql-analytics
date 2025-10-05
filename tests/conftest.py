import os
import pytest
import psycopg

from text2sql_analytics.data_loader import DataLoader, LoaderConfig


@pytest.fixture(scope="session", autouse=False)
def ensure_env_defaults(tmp_path_factory):
    os.environ.setdefault("DB_HOST", "localhost")
    os.environ.setdefault("DB_PORT", "5433")
    os.environ.setdefault("DB_NAME", "northwind")
    os.environ.setdefault("DB_USER_RO", "ro")
    os.environ.setdefault("DB_PASS_RO", "changeme")
    os.environ.setdefault("QUERY_TIMEOUT_SECONDS", "5")
    os.environ.setdefault("ROW_LIMIT", "1000")
    yield


@pytest.fixture(scope="session", autouse=True)
def prepare_schema_and_seed(ensure_env_defaults):
    """Ensure base schema exists and minimal data is present for accuracy tests.

    Uses admin credentials to create schema and seed a minimal product/category
    if tables are empty. Skips quietly if database is unreachable.
    """
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5433"))
    dbname = os.getenv("DB_NAME", "northwind")
    admin_user = os.getenv("DB_USER_ADMIN", "admin")
    admin_pass = os.getenv("DB_PASS_ADMIN", "changeme")

    try:
        cfg = LoaderConfig(
            db_host=host,
            db_port=port,
            db_name=dbname,
            db_user=admin_user,
            db_pass=admin_pass,
        )
        DataLoader(cfg).create_normalized_schema()

        with psycopg.connect(
            host=host, port=port, dbname=dbname, user=admin_user, password=admin_pass, autocommit=True
        ) as conn, conn.cursor() as cur:
            # Ensure at least one category
            cur.execute(
                """
                INSERT INTO public.categories (category_id, category_name)
                VALUES (1, 'General')
                ON CONFLICT (category_id) DO NOTHING
                """
            )
            # If products empty, seed one row to satisfy tests
            cur.execute("SELECT COUNT(*) FROM public.products")
            if cur.fetchone()[0] == 0:  # type: ignore[index]
                cur.execute(
                    """
                    INSERT INTO public.products (
                        product_id, product_name, supplier_id, category_id, quantity_per_unit,
                        unit_price, units_in_stock, units_on_order, reorder_level, discontinued
                    ) VALUES (1, 'Sample', 1, 1, '1 unit', 10.0, 10, 0, 0, 0)
                    ON CONFLICT (product_id) DO NOTHING
                    """
                )
    except Exception:
        # DB may be unavailable in some environments; do not fail test discovery
        pass
