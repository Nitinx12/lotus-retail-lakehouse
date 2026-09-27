# lotus retail lakehouse control plane per architecture sections 2 3 11 and 12
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.databricks.operators.databricks import (
    DatabricksSubmitRunOperator,
)
from airflow.providers.postgres.operators.postgres import PostgresOperator


# resolves the active environment without branching task bodies on its name
def resolve_env() -> str:
    try:
        return Variable.get("LOTUS_ENV", default_var=os.getenv("LOTUS_ENV", "dev"))
    except Exception:
        return os.getenv("LOTUS_ENV", "dev")


# routes task failures and sla misses to the alert channel
def notify_on_failure(context: object) -> None:
    import json
    import urllib.request

    if isinstance(context, dict) and context.get("task_instance") is not None:
        task = context["task_instance"]
        text = (
            f"lotus task failed: {task.dag_id}.{task.task_id} "
            f"run {task.run_id} state {task.state}"
        )
    else:
        text = f"lotus sla miss: {getattr(context, 'dag_id', context)}"
    url = os.getenv("SLACK_WEBHOOK_URL", "")
    if url and "CHANGEME" not in url:
        urllib.request.urlopen(
            urllib.request.Request(
                url,
                data=json.dumps({"text": text}).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=10,
        )


# runs one great expectations checkpoint suite for the given layer
def checkpoint(suite: str, env: str) -> None:
    subprocess.run(
        ["uv", "run", "python", "scripts/run_gx.py", "--suite", suite],
        check=True,
        env={**os.environ, "LOTUS_ENV": env},
    )


LOTUS_ENV = resolve_env()

ENV_CONFIG = {
    "dev": {
        "catalog": "dev_lotus",
        "gold_schema": "lotus_gold_dev",
        "ops_conn": "postgres_ops_dev",
        "databricks_conn": "databricks_dev",
    },
    "staging": {
        "catalog": "staging_lotus",
        "gold_schema": "lotus_gold_staging",
        "ops_conn": "postgres_ops_staging",
        "databricks_conn": "databricks_staging",
    },
    "prod": {
        "catalog": "prod_lotus",
        "gold_schema": "lotus_gold_prod",
        "ops_conn": "postgres_ops_prod",
        "databricks_conn": "databricks_prod",
    },
}
CFG = ENV_CONFIG[LOTUS_ENV]


# builds the job cluster spec shared by every databricks task
def job_cluster(layer: str) -> dict:
    return {
        "new_cluster": {
            "spark_version": "15.4.x-scala2.12",
            "num_workers": 2,
            "node_type_id": "Standard_DS3_v2",
            "custom_tags": {
                "env": LOTUS_ENV,
                "pipeline": "lotus",
                "layer": layer,
            },
        },
        "notebook_task": {"notebook_path": f"/lotus/{layer}"},
    }


with DAG(
    dag_id="lotus_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "lotus",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "retry_exponential_backoff": True,
        "on_failure_callback": notify_on_failure,
    },
    sla_miss_callback=notify_on_failure,
    tags=["lotus", LOTUS_ENV],
) as dag:
    source_checks = PostgresOperator(
        task_id="plpgsql_source_checks",
        postgres_conn_id=CFG["ops_conn"],
        sql="sql/plpgsql_checks/source_checks.sql",
        sla=timedelta(minutes=10),
    )

    bronze = DatabricksSubmitRunOperator(
        task_id="bronze",
        databricks_conn_id=CFG["databricks_conn"],
        sla=timedelta(minutes=20),
        **job_cluster("bronze"),
    )

    gx_bronze = PythonOperator(
        task_id="gx_bronze",
        python_callable=checkpoint,
        op_kwargs={"suite": "bronze", "env": LOTUS_ENV},
        sla=timedelta(minutes=10),
    )

    silver = DatabricksSubmitRunOperator(
        task_id="silver",
        databricks_conn_id=CFG["databricks_conn"],
        sla=timedelta(minutes=20),
        **job_cluster("silver"),
    )

    gx_silver = PythonOperator(
        task_id="gx_silver",
        python_callable=checkpoint,
        op_kwargs={"suite": "silver", "env": LOTUS_ENV},
        sla=timedelta(minutes=10),
    )

    gold = DatabricksSubmitRunOperator(
        task_id="gold",
        databricks_conn_id=CFG["databricks_conn"],
        sla=timedelta(minutes=20),
        **job_cluster("gold"),
    )

    gx_gold = PythonOperator(
        task_id="gx_gold",
        python_callable=checkpoint,
        op_kwargs={"suite": "gold", "env": LOTUS_ENV},
        sla=timedelta(minutes=10),
    )

    jdbc_to_postgres = BashOperator(
        task_id="jdbc_to_postgres",
        bash_command="bash scripts/run_publish.sh",
        sla=timedelta(minutes=15),
    )

    plpgsql_gold_checks = PostgresOperator(
        task_id="plpgsql_gold_checks",
        postgres_conn_id=CFG["ops_conn"],
        sql="sql/plpgsql_checks/gold_checks.sql",
        sla=timedelta(minutes=10),
    )

    dbt = BashOperator(
        task_id="dbt",
        bash_command="dbt run --target "
        + LOTUS_ENV
        + " && dbt test --target "
        + LOTUS_ENV,
        sla=timedelta(minutes=15),
    )

    r_analysis = BashOperator(
        task_id="r_analysis",
        bash_command="bash scripts/run_report.sh",
        sla=timedelta(minutes=20),
    )

    latex_report = BashOperator(
        task_id="latex_report",
        bash_command="latexmk -pdf -outdir=reports reports/report.tex",
        sla=timedelta(minutes=20),
    )

    streamlit_refresh = BashOperator(
        task_id="streamlit_refresh",
        bash_command="touch reports/.streamlit_refresh",
        sla=timedelta(minutes=5),
    )

    docker_build = BashOperator(
        task_id="docker_build",
        bash_command="docker build -f Dockerfile.pipeline -t lotus-pipeline:"
        + LOTUS_ENV
        + " .",
        sla=timedelta(minutes=20),
    )

    push = BashOperator(
        task_id="push",
        bash_command="docker push lotus-pipeline:"
        + LOTUS_ENV
        + " && git push origin HEAD",
        sla=timedelta(minutes=15),
    )

    (
        source_checks
        >> bronze
        >> gx_bronze
        >> silver
        >> gx_silver
        >> gold
        >> gx_gold
        >> jdbc_to_postgres
        >> plpgsql_gold_checks
        >> dbt
    )
    dbt >> r_analysis >> latex_report >> docker_build >> push
    dbt >> streamlit_refresh >> docker_build
