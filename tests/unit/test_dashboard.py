# unit tests for dashboard helpers
from datetime import UTC, datetime

from dashboard.lib.db import gold_stale, pool_dsn


# checks pool dsn points at the pooler port
def test_pool_dsn() -> None:
    dsn = pool_dsn("lotus_gold_dev", "lotus_app", "pw")
    assert "port=6432" in dsn
    assert "dbname=lotus_gold_dev" in dsn
    assert "password=pw" in dsn


# checks fresh gold passes the sla
def test_gold_fresh() -> None:
    now = datetime(2024, 6, 1, 4, 0, tzinfo=UTC)
    last = datetime(2024, 6, 1, 2, 0, tzinfo=UTC)
    assert gold_stale(now, last) is False


# checks old gold trips the sla banner
def test_gold_stale() -> None:
    now = datetime(2024, 6, 1, 4, 0, tzinfo=UTC)
    assert gold_stale(now, None) is True
    last = datetime(2024, 5, 30, 2, 0, tzinfo=UTC)
    assert gold_stale(now, last) is True
