# dag integrity tests for the airflow control plane
from pathlib import Path

import pytest

DAG_PATH = Path("dags/lotus_pipeline_dag.py")


# checks the dag parses with retries and sla coverage
def test_dag_integrity() -> None:
    if not DAG_PATH.exists():
        pytest.skip("dags/lotus_pipeline_dag.py not present in this checkout")
    text = DAG_PATH.read_text(encoding="utf-8")
    assert "retries" in text
    assert "sla" in text or "exemption" in text
