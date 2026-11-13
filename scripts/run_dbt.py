"""CLI wrapper for the dbt build."""

from eng_workbench.dbt_job import run_dbt

if __name__ == "__main__":
    raise SystemExit(run_dbt())
