import os

import pytest

from eng_workbench.gates import classify_url, ensure_local
from eng_workbench.store import PgDatabase, Store


def test_postgres_semantic_model() -> None:
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("DATABASE_URL is not a local postgres URL")
    if classify_url(url, allow_remote=False) != "local":
        pytest.skip("DATABASE_URL is not local")
    ensure_local(url, allow_remote=False)
    import psycopg

    conn = psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://", 1))
    conn.autocommit = True
    conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
    conn.execute("CREATE SCHEMA public")
    store = Store(PgDatabase(conn))
    store.apply_schema()
    store.load_lab()
    rates = {row["build_id"]: row["pass_rate"] for row in store.pass_rates("SYN-TENANT-RIDGEBENCH")}
    assert rates["SYN-FW-417"] == pytest.approx(21 / 40)
    assert store.dq_count() == 9
    conn.close()
