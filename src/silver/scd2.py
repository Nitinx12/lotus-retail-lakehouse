# slowly changing dimension type 2 versioning
from __future__ import annotations

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.column import Column

from src.spark.dates import safe_to_date

HASH_COL = "attribute_hash"

# tracked attributes per ARCHITECTURE section 7
CUSTOMER_TRACKED = ["region", "loyalty_tier"]
EMPLOYEE_TRACKED = ["store_id", "role"]


# hashes tracked attributes into one comparable string
def attribute_hash(df: DataFrame, cols: list[str]) -> Column:
    parts = [F.coalesce(F.col(c).cast("string"), F.lit("")) for c in cols]
    return F.md5(F.concat_ws("|", *parts))


# drops run tracking columns that must not take part in versioning
def drop_batch(df: DataFrame) -> DataFrame:
    return df.drop(
        *[c for c in df.columns if c.startswith("_batch_id") or c == "_rescued_data"]
    )


# coerces legacy effective dates to date for compatible unions
def normalize_dates(df: DataFrame) -> DataFrame:
    out = df
    if "effective_start_date" in out.columns:
        out = out.withColumn(
            "effective_start_date", safe_to_date("effective_start_date")
        )
    if "effective_end_date" in out.columns:
        out = out.withColumn("effective_end_date", safe_to_date("effective_end_date"))
    return out


# merges incoming rows into a versioned scd2 table
def apply_scd2(
    current: DataFrame | None,
    incoming: DataFrame,
    natural_key: str,
    tracked: list[str],
    sk_col: str,
    business_date: str,
) -> DataFrame:
    incoming = drop_batch(incoming)
    if current is not None:
        current = normalize_dates(drop_batch(current))
    fresh = dedupe_incoming(incoming, natural_key)
    fresh = fresh.withColumn(HASH_COL, attribute_hash(fresh, tracked))
    if current is None or current.limit(1).count() == 0:
        return first_load(fresh, sk_col, business_date)
    assert_no_duplicate_current(current, natural_key)
    return merge_versions(current, fresh, natural_key, sk_col, business_date)


# dedupes one batch keeping the last row per natural key
def dedupe_incoming(df: DataFrame, natural_key: str) -> DataFrame:
    ordered = df.withColumn("_row_pos", F.monotonically_increasing_id())
    window = Window.partitionBy(natural_key).orderBy(F.col("_row_pos").desc())
    return (
        ordered.withColumn("_rank", F.row_number().over(window))
        .filter(F.col("_rank") == 1)
        .drop("_rank", "_row_pos")
    )


# builds the initial versioned table with sequential surrogate keys
def first_load(fresh: DataFrame, sk_col: str, business_date: str) -> DataFrame:
    window = Window.orderBy(F.monotonically_increasing_id())
    return (
        fresh.withColumn(sk_col, F.row_number().over(window))
        .withColumn("effective_start_date", F.to_date(F.lit(business_date)))
        .withColumn("effective_end_date", F.lit(None).cast("date"))
        .withColumn("is_current", F.lit(True))
    )


# fails loudly when history holds two current rows for one key
def assert_no_duplicate_current(current: DataFrame, natural_key: str) -> None:
    dupes = (
        current.filter(F.col("is_current") == True)
        .groupBy(natural_key)
        .count()
        .filter(F.col("count") > 1)
        .limit(5)
        .collect()
    )
    if dupes:
        keys = [r[natural_key] for r in dupes]
        raise ValueError(
            f"scd2 {natural_key} has several current rows for keys={keys} count={len(keys)}"
        )


# closes changed rows and inserts new plus brand new keys
def merge_versions(
    current: DataFrame,
    fresh: DataFrame,
    natural_key: str,
    sk_col: str,
    business_date: str,
) -> DataFrame:
    cur_open = current.filter(F.col("is_current") == True).select(
        natural_key, F.col(HASH_COL).alias(f"{HASH_COL}_right")
    )
    joined = fresh.join(cur_open, on=natural_key, how="left")
    changed_keys = (
        joined.filter(
            F.col(f"{HASH_COL}_right").isNotNull()
            & (F.col(HASH_COL) != F.col(f"{HASH_COL}_right"))
        )
        .select(natural_key)
        .distinct()
    )
    new_keys = joined.filter(F.col(f"{HASH_COL}_right").isNull()).select(fresh.columns)
    changed_rows = fresh.join(changed_keys, on=natural_key, how="inner")
    closed = (
        current.join(changed_keys, on=natural_key, how="left_semi")
        .withColumn("is_current", F.lit(False))
        .withColumn("effective_end_date", F.to_date(F.lit(business_date)))
    )
    untouched = current.join(changed_keys, on=natural_key, how="left_anti")
    inserts = new_keys.unionByName(changed_rows, allowMissingColumns=True)
    max_sk = current.agg(F.max(sk_col)).collect()[0][0]
    max_sk = int(max_sk) if max_sk is not None else 0
    window = Window.orderBy(F.monotonically_increasing_id())
    inserts = (
        inserts.withColumn("_rank", F.row_number().over(window))
        .withColumn(sk_col, F.col("_rank") + F.lit(max_sk))
        .drop("_rank")
        .withColumn("effective_start_date", F.to_date(F.lit(business_date)))
        .withColumn("effective_end_date", F.lit(None).cast("date"))
        .withColumn("is_current", F.lit(True))
    )
    base_cols = untouched.columns
    return untouched.unionByName(
        closed.select(base_cols), allowMissingColumns=True
    ).unionByName(inserts.select(base_cols), allowMissingColumns=True)


# joins facts to the dimension version active on the fact date
def asof_join(
    facts: DataFrame,
    dim: DataFrame,
    natural_key: str,
    sk_col: str,
    fact_date_col: str,
    suffix: str = "",
) -> DataFrame:
    from pyspark.sql.functions import broadcast as _broadcast

    renamed = drop_batch(dim)
    overlap = set(facts.columns) & set(renamed.columns) - {natural_key}
    tag = suffix or "_dim"
    for c in sorted(overlap):
        renamed = renamed.withColumnRenamed(c, f"{c}{tag}")
    start = (
        f"effective_start_date{tag}"
        if f"effective_start_date{tag}" in renamed.columns
        else "effective_start_date"
    )
    end = (
        f"effective_end_date{tag}"
        if f"effective_end_date{tag}" in renamed.columns
        else "effective_end_date"
    )
    dim_typed = renamed.withColumn(start, safe_to_date(start)).withColumn(
        end, safe_to_date(end)
    )
    facts_typed = facts.withColumn("_fdate", safe_to_date(fact_date_col)).withColumn(
        "_pos", F.monotonically_increasing_id()
    )
    joined = facts_typed.join(_broadcast(dim_typed), on=natural_key, how="left")
    window = Window.partitionBy("_pos").orderBy(F.col(start).desc_nulls_last())
    active = (
        joined.withColumn(
            "_active",
            (F.col(start) <= F.col("_fdate"))
            & (F.col(end).isNull() | (F.col("_fdate") < F.col(end))),
        )
        .filter(F.col("_active"))
        .withColumn("_rank", F.row_number().over(window))
        .filter(F.col("_rank") == 1)
        .drop("_active", "_rank", "_fdate")
    )
    missing = facts_typed.join(active.select("_pos"), on="_pos", how="left_anti").drop(
        "_fdate"
    )
    fill = missing.join(dim_typed.limit(0), on=natural_key, how="left")
    base = active.drop("_pos")
    return base.unionByName(fill.drop("_pos"), allowMissingColumns=True)
