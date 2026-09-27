# integration tests for gx checkpoint blocking
import pandas as pd
import pytest

from tests.integration.test_run_tracking import ops_conn

psycopg2 = pytest.importorskip("psycopg2")


# checks a failing checkpoint blocks and records the failure
def test_gx_blocks_on_failure(monkeypatch, tmp_path) -> None:
    import scripts.run_gx as gx
    from src.quality.gx_suites import silver_checks

    bad = pd.DataFrame(
        [
            {"customer_id": "a", "gender": "X"},
            {"customer_id": "a", "gender": "X"},
        ]
    )
    (tmp_path / "silver").mkdir()
    bad.to_parquet(tmp_path / "silver" / "dim_customers.parquet")
    monkeypatch.setattr(gx, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        gx,
        "layer_plan",
        lambda layer: {"dim_customers.parquet": silver_checks("dim_customers")},
    )
    monkeypatch.setattr("sys.argv", ["run_gx", "--suite", "silver"])
    with pytest.raises(SystemExit) as exc:
        gx.main()
    assert exc.value.code == 1
    conn = ops_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT success_percent, failed_expectations "
                "FROM ops.quality_results WHERE suite_name = 'gx_silver' "
                "ORDER BY checked_at DESC LIMIT 1"
            )
            pct, failed = cur.fetchone()
    finally:
        conn.close()
    assert pct < 100.0
    assert failed > 0
