# unit tests for ops dsn helpers
from src.ops.db import build_dsn


# checks libpq dsn formatting
def test_build_dsn() -> None:
    assert (
        build_dsn("localhost", 5432, "lotus_ops_dev", "lotus_ops", "pw")
        == "host=localhost port=5432 dbname=lotus_ops_dev user=lotus_ops password=pw"
    )
