# unit tests for the gold publish contract
from scripts.run_publish import GOLD_SCHEMA, TABLES


# checks serving tables exclude dbt owned marts
def test_publish_tables() -> None:
    assert GOLD_SCHEMA == "gold"
    assert "dim_customers" in TABLES
    assert "fact_orders" in TABLES
    assert not [t for t in TABLES if t.startswith("mart_")]
