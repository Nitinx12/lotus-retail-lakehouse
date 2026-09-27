# integration tests for failure row durability
import os
import uuid

import pytest

psycopg2 = pytest.importorskip("psycopg2")


# opens ops or skips when postgres is unreachable
def ops_conn():
    try:
        return psycopg2.connect(
            host=os.getenv("POSTGRES_OPS_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_OPS_PORT", "5432")),
            dbname=os.getenv("POSTGRES_OPS_DB", "lotus_ops_dev"),
            user=os.getenv("POSTGRES_OPS_USER", "lotus_ops"),
            password=os.getenv("POSTGRES_OPS_PASSWORD", ""),
            connect_timeout=3,
        )
    except psycopg2.Error:
        pytest.skip("postgres unreachable")


# checks a crashed stage still leaves its failed row behind
def test_failed_run_persists(monkeypatch) -> None:
    import scripts.run_silver as silver

    marker = f"boom-{uuid.uuid4()}"

    def _boom(*args, **kwargs):
        raise RuntimeError(marker)

    monkeypatch.setattr("pandas.read_parquet", _boom)
    with pytest.raises(RuntimeError):
        silver.main()
    conn = ops_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, error_message FROM ops.pipeline_runs "
                "WHERE task_name = 'silver' AND status = 'failed' "
                "ORDER BY started_at DESC LIMIT 1"
            )
            status, error = cur.fetchone()
    finally:
        conn.close()
    assert status == "failed"
    assert marker in error
