# spark session factory for local runs and databricks jobs
from __future__ import annotations

import os

from pyspark.sql import SparkSession


# resolves the active lotus environment without branching callers
def resolve_env(default: str = "dev") -> str:
    return os.getenv("LOTUS_ENV", default)


# resolves the unity catalog name for the active environment
def catalog_for(env: str) -> str:
    return {"dev": "dev_lotus", "staging": "staging_lotus", "prod": "prod_lotus"}.get(
        env, os.getenv("DATABRICKS_CATALOG", "dev_lotus")
    )


# builds one shared spark session with adaptive execution enabled
def get_spark(app: str = "lotus") -> SparkSession:
    if os.getenv("LOTUS_SPARK", "local") == "remote":
        from databricks.connect import DatabricksSession

        return DatabricksSession.builder.serverless(True).getOrCreate()
    builder = SparkSession.builder.appName(app)
    builder = builder.config("spark.sql.adaptive.enabled", "true")
    builder = builder.config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    builder = builder.config("spark.sql.adaptive.skewJoin.enabled", "true")
    builder = builder.config("spark.sql.shuffle.partitions", "8")
    builder = builder.config("spark.sql.broadcastTimeout", "600")
    builder = builder.config("spark.sql.execution.arrow.pyspark.enabled", "true")
    existing = SparkSession.getActiveSession()
    if existing is not None:
        return existing
    return builder.getOrCreate()
