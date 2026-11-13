# ADR 0002 — dbt runs, Airflow does not

## Status

Accepted.

## Context

The semantic model is three SQL selects. The app executes them as SQLite views. The same selects are dbt models over generated seeds.

Airflow would only call the same four task names: ingest, quality, semantic, metrics. No scheduler was available here, and Docker was not installed.

## Decision

Run `dbt build` in pytest against DuckDB. Keep `orchestration/dags/lab_pipeline.py` as a task list that imports Airflow only inside `build_dag`. That function is not called. The test checks the task tuple and that `airflow.models` is not installed.

## Consequences

The committed proof of the semantic model is the pytest comparison of `SYN-FW-417` pass rate. The DAG file is not evidence that a scheduler ran.
