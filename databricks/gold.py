# databricks gold job building the star schema per architecture section 8
from __future__ import annotations

from src.gold.build import (
    build_fact_orders,
    build_fact_returns,
    mart_ramadan_seasonality,
    mart_return_rate_by_product,
    mart_revenue_by_store_month,
)
from src.spark.session import catalog_for, get_spark, resolve_env


# builds dimensions, facts, and marts then optimizes the fact table
def main() -> None:
    catalog = catalog_for(resolve_env())
    spark = get_spark("lotus-gold")

    def silver(table: str):
        return spark.read.table(f"{catalog}.silver.{table}")

    def write(frame, table: str) -> None:
        frame.write.format("delta").mode("overwrite").saveAsTable(
            f"{catalog}.gold.{table}"
        )

    for table in ("dim_date", "dim_stores", "dim_products"):
        write(silver(table), table)
    for table in ("dim_customers", "dim_employees"):
        write(silver(f"{table}_scd2"), table)
    customers = spark.read.table(f"{catalog}.gold.dim_customers")
    employees = spark.read.table(f"{catalog}.gold.dim_employees")
    facts = build_fact_orders(silver("fact_orders"), customers, employees)
    write(facts, "fact_orders")
    fact_returns = build_fact_returns(silver("fact_returns"), facts)
    write(fact_returns, "fact_returns")
    write(silver("fact_order_details"), "fact_order_details")
    write(mart_revenue_by_store_month(facts), "mart_revenue_by_store_month")
    write(
        mart_return_rate_by_product(silver("fact_order_details"), fact_returns),
        "mart_return_rate_by_product",
    )
    write(
        mart_ramadan_seasonality(facts, spark.read.table(f"{catalog}.gold.dim_date")),
        "mart_ramadan_seasonality",
    )
    spark.sql(f"OPTIMIZE {catalog}.gold.fact_orders ZORDER BY (store_id, order_date)")
    spark.sql(f"VACUUM {catalog}.gold.fact_orders RETAIN 7 DAYS")


if __name__ == "__main__":
    main()
