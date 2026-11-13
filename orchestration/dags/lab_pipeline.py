"""Airflow sketch. Importing this module does not start a scheduler.

The scheduler was not run. Docker is not installed on the workstation that
built this repository, so no Airflow container was started either.
"""

TASKS = ("ingest", "quality", "semantic", "metrics")


def build_dag():  # type: ignore[no-untyped-def]
    from airflow import DAG
    from airflow.operators.empty import EmptyOperator

    with DAG(dag_id="ridgebench_lab", schedule=None, catchup=False) as dag:
        previous = None
        for name in TASKS:
            step = EmptyOperator(task_id=name)
            if previous is not None:
                previous >> step
            previous = step
    return dag
