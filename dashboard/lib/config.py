# env driven dashboard settings with pooler first defaults
from __future__ import annotations

import os


# returns the first set variable in names else the default
def _setting(names: list[str], default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "")
        if value:
            return value
    return default


LOTUS_ENV = os.getenv("LOTUS_ENV", "dev")
PG_HOST = _setting(
    ["POSTGRES_GOLD_POOL_HOST", "POSTGRES_GOLD_HOST", "LOTUS_PGHOST", "PGHOST"],
    "localhost",
)
PG_PORT = int(
    _setting(
        ["POSTGRES_GOLD_POOL_PORT", "POSTGRES_GOLD_PORT", "LOTUS_PGPORT", "PGPORT"],
        "6432",
    )
)
PG_DATABASE = _setting(
    ["POSTGRES_GOLD_DB", "LOTUS_PGDATABASE", "PGDATABASE"], "lotus_gold_dev"
)
PG_USER = _setting(["POSTGRES_GOLD_USER", "LOTUS_PGUSER", "PGUSER"], "lotus_app")
PG_PASSWORD = _setting(["POSTGRES_GOLD_PASSWORD", "LOTUS_PGPASSWORD", "PGPASSWORD"], "")
PG_SSLMODE = "require" if LOTUS_ENV == "prod" else "prefer"
MART_SCHEMA = os.getenv("LOTUS_MART_SCHEMA", "marts")
DATA_TTL_SECONDS = int(os.getenv("LOTUS_DASH_TTL", "300"))
OPS_TTL_SECONDS = int(os.getenv("LOTUS_OPS_TTL", "30"))
GOLD_FRESHNESS_SLA_HOURS = 24
PALETTE = {
    "navy": "#1B4B66",
    "blue": "#2E86AB",
    "lightblue": "#5DA9C4",
    "magenta": "#A23B72",
    "orange": "#D68C45",
    "green": "#3A7D44",
    "grey": "#8E8E8E",
}
CURRENCY_PREFIX = "EGP "
PII_ROLES = {"admin", "pii_reader"}
