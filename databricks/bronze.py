# databricks bronze job reading mongo into delta per architecture section 5
from __future__ import annotations

import os

from src.bronze.ingest import normalize_frame
from src.spark.session import catalog_for, get_spark, resolve_env

TABLES = [
    "dim_date",
    "dim_stores",
    "dim_customers",
    "dim_employees",
    "dim_products",
    "fact_orders_2022_2023",
    "fact_orders_2024",
    "fact_order_details",
    "fact_returns",
]


# loads every raw collection into its bronze delta table
def main() -> None:
    env = resolve_env()
    catalog = catalog_for(env)
    mongo_uri = os.environ["MONGO_URI"]
    database = os.getenv("MONGO_DATABASE", "lotus_retail")
    spark = get_spark("lotus-bronze")
    for table in TABLES:
        frame = normalize_frame(
            spark.read.format("mongodb")
            .option("connection.uri", mongo_uri)
            .option("database", database)
            .option("collection", table)
            .load()
        )
        frame.write.format("delta").option("mergeSchema", "true").mode(
            "overwrite"
        ).saveAsTable(f"{catalog}.bronze.{table}")


if __name__ == "__main__":
    main()
