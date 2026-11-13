from eng_workbench.dbt_job import dbt_executable, duckdb_path, run_dbt
from eng_workbench.identity import TENANT
from eng_workbench.store import build_lab_store


def test_dbt_build_matches_the_sqlite_pass_rate() -> None:
    assert dbt_executable().is_file()
    assert run_dbt() == 0
    import duckdb

    conn = duckdb.connect(str(duckdb_path()), read_only=True)
    row = conn.execute(
        """
        select pass_rate from build_quality
        where tenant_id = ? and build_id = 'SYN-FW-417'
        """,
        [TENANT],
    ).fetchone()
    conn.close()
    assert row is not None
    store = build_lab_store(include_dirty=False)
    app_rate = next(
        item["pass_rate"] for item in store.pass_rates(TENANT) if item["build_id"] == "SYN-FW-417"
    )
    assert abs(float(row[0]) - float(app_rate)) < 1e-9
