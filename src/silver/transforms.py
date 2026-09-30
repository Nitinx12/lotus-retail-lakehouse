# pure cleaning transforms for the silver layer
from __future__ import annotations

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from src.spark.dates import safe_to_date


# drops duplicate rows on the natural key keeping the chosen survivor
def dedupe(df: DataFrame, keys: list[str], keep: str = "first") -> DataFrame:
    if keep == "first":
        return df.dropDuplicates(keys)
    ordered = df.withColumn("_row_pos", F.monotonically_increasing_id())
    window = Window.partitionBy(*keys).orderBy(F.col("_row_pos").desc())
    return (
        ordered.withColumn("_rank", F.row_number().over(window))
        .filter(F.col("_rank") == 1)
        .drop("_rank", "_row_pos")
    )


# drops mongo extract metadata that must not reach serving tables
def drop_extract_meta(df: DataFrame) -> DataFrame:
    return df.drop("loaded_at") if "loaded_at" in df.columns else df


# strips surrounding whitespace on the given string columns
def strip_text(df: DataFrame, cols: list[str]) -> DataFrame:
    out = df
    for c in cols:
        if c in out.columns:
            out = out.withColumn(
                c,
                F.when(F.col(c).isNull(), F.lit(None)).otherwise(
                    F.trim(F.col(c).cast("string"))
                ),
            )
    return out


# title cases gender variants into Male and Female
def normalize_gender(df: DataFrame, col: str = "gender") -> DataFrame:
    if col not in df.columns:
        return df
    trimmed = F.trim(F.col(col).cast("string"))
    lowered = F.lower(trimmed)
    return df.withColumn(
        col,
        F.when(F.col(col).isNull(), F.lit(None))
        .when(lowered == "male", F.lit("Male"))
        .when(lowered == "female", F.lit("Female"))
        .otherwise(trimmed),
    )


# cleans dim_customers fixing dupes, case, phone type, and dates
def clean_customers(df: DataFrame) -> DataFrame:
    out = drop_extract_meta(df)
    out = out.filter(F.col("customer_id").isNotNull() & (F.col("customer_id") != ""))
    out = dedupe(out, ["customer_id"], keep="last")
    out = strip_text(out, ["full_name", "city", "region", "loyalty_tier", "email"])
    out = normalize_gender(out)
    out = out.withColumn("phone", F.col("phone").cast("string"))
    for c in ("birth_date", "registration_date"):
        if c in out.columns:
            out = out.withColumn(c, safe_to_date(c))
    return out


# splits pipe separated product names into name, color, and size
def split_product_name(df: DataFrame, col: str = "product_name_raw") -> DataFrame:
    parts = F.split(F.col(col).cast("string"), r"\|")
    out = df.withColumn("product_name", F.trim(parts.getItem(0)))
    out = out.withColumn(
        "color",
        F.when(F.size(parts) > 1, F.trim(parts.getItem(1))).otherwise(F.lit(None)),
    )
    out = out.withColumn(
        "size",
        F.when(F.size(parts) > 2, F.trim(parts.getItem(2))).otherwise(F.lit(None)),
    )
    return out.drop(col)


# cleans dim_products splitting names and dropping the redundant price text
def clean_products(df: DataFrame) -> DataFrame:
    out = drop_extract_meta(df)
    out = dedupe(out, ["product_id"])
    out = strip_text(out, ["category", "subcategory", "brand"])
    out = split_product_name(out)
    return out.drop("unit_price_text") if "unit_price_text" in out.columns else out


# cleans one fact_orders frame trimming text and parsing dates
def clean_orders(df: DataFrame) -> DataFrame:
    out = drop_extract_meta(df)
    out = strip_text(
        out,
        ["payment_method", "order_status", "customer_id", "employee_id", "order_id"],
    )
    out = out.withColumn(
        "employee_id",
        F.when(
            F.col("employee_id").isNull() | (F.col("employee_id") == ""),
            F.lit(None),
        ).otherwise(F.col("employee_id")),
    )
    out = out.filter(F.col("order_id").isNotNull() & (F.col("order_id") != ""))
    return out.withColumn("order_date", safe_to_date("order_date"))


# unions the two orders frames into one deduplicated frame
def union_orders(first: DataFrame, second: DataFrame) -> DataFrame:
    return dedupe(first.unionByName(second, allowMissingColumns=True), ["order_id"])


# enriches returns with per order item count and revenue from details
def enrich_returns(returns: DataFrame, details: DataFrame) -> DataFrame:
    agg = details.groupBy("order_id").agg(
        F.count("product_id").alias("n_items"),
        F.sum("line_total_revenue").alias("order_revenue"),
    )
    out = returns.join(agg, on="order_id", how="left")
    out = out.withColumn("return_orphan", F.col("n_items").isNull())
    out = out.withColumn("return_date", safe_to_date("return_date"))
    return strip_text(out, ["return_reason", "refund_method", "return_status"])
