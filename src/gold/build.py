# pure builders for the gold star schema and marts
from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast as _broadcast

from src.silver.scd2 import asof_join
from src.spark.dates import safe_to_date


# resolves order facts to customer and employee versions active at order time
def build_fact_orders(
    orders: DataFrame, customers: DataFrame, employees: DataFrame
) -> DataFrame:
    with_customers = asof_join(
        orders, customers, "customer_id", "customer_sk", "order_date"
    )
    emp = employees.select(
        "employee_id",
        "employee_sk",
        "effective_start_date",
        "effective_end_date",
    )
    out = asof_join(
        with_customers, emp, "employee_id", "employee_sk", "order_date", "_emp"
    )
    return drop_batch(out)


# attaches customer and store keys to returns through their order
def build_fact_returns(returns: DataFrame, orders: DataFrame) -> DataFrame:
    keys = orders.select(
        "order_id", "customer_sk", "employee_sk", "store_id"
    ).dropDuplicates(["order_id"])
    out = returns.join(_broadcast(keys), on="order_id", how="left")
    return drop_batch(out)


# aggregates monthly revenue and cost per store
def mart_revenue_by_store_month(orders: DataFrame) -> DataFrame:
    out = orders.withColumn(
        "month", F.date_format(safe_to_date("order_date"), "yyyy-MM")
    )
    return (
        out.groupBy("store_id", "month")
        .agg(
            F.sum("total_revenue").alias("revenue"),
            F.sum("total_cost").alias("cost"),
            F.countDistinct("order_id").alias("orders"),
        )
        .orderBy("store_id", "month")
    )


# computes return rate per product from details and returned order ids
def mart_return_rate_by_product(
    details: DataFrame, returned_ids: DataFrame | list
) -> DataFrame:
    if isinstance(returned_ids, DataFrame):
        flagged = (
            details.join(
                _broadcast(
                    returned_ids.select("order_id")
                    .distinct()
                    .withColumn("_returned", F.lit(1))
                ),
                on="order_id",
                how="left",
            )
            .withColumn(
                "was_returned",
                F.when(F.col("_returned") == 1, F.lit(1)).otherwise(F.lit(0)),
            )
            .drop("_returned")
        )
    else:
        flagged = details.withColumn(
            "was_returned",
            F.when(F.col("order_id").isin(list(returned_ids)), F.lit(1)).otherwise(
                F.lit(0)
            ),
        )
    agg = flagged.groupBy("product_id").agg(
        F.count("order_id").alias("times_ordered"),
        F.sum("was_returned").alias("times_returned"),
    )
    return agg.withColumn(
        "return_rate", F.col("times_returned") / F.col("times_ordered")
    ).orderBy(F.col("return_rate").desc())


# compares monthly revenue inside versus outside ramadan
def mart_ramadan_seasonality(orders: DataFrame, dates: DataFrame) -> DataFrame:
    out = orders.join(
        _broadcast(dates.select("date_id", "is_ramadan")), on="date_id", how="left"
    )
    out = out.withColumn("month", F.date_format(safe_to_date("order_date"), "yyyy-MM"))
    agg = (
        out.groupBy("month", "is_ramadan")
        .agg(
            F.sum("total_revenue").alias("revenue"),
            F.countDistinct("order_id").alias("orders"),
        )
        .orderBy("month")
    )
    return drop_batch(agg)


# drops run tracking columns that must not reach serving tables
def drop_batch(df: DataFrame) -> DataFrame:
    return df.drop(
        *[c for c in df.columns if c.startswith("_batch_id") or c == "_rescued_data"]
    )
