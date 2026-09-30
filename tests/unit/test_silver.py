# unit tests for silver cleaning transforms
from pyspark.sql import SparkSession

from src.silver.transforms import (
    clean_customers,
    clean_orders,
    dedupe,
    drop_extract_meta,
    enrich_returns,
    normalize_gender,
    split_product_name,
    strip_text,
    union_orders,
)


# checks dedupe keeps the first row per key
def test_dedupe(spark: SparkSession) -> None:
    df = spark.createDataFrame([{"id": "a", "v": 1}, {"id": "a", "v": 2}])
    assert dedupe(df, ["id"]).count() == 1


# checks whitespace stripping
def test_strip_text(spark: SparkSession) -> None:
    df = spark.createDataFrame([{"p": "  Cash  "}])
    assert strip_text(df, ["p"]).collect()[0]["p"] == "Cash"


# checks gender variants collapse
def test_normalize_gender(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [{"gender": "MALE"}, {"gender": "female"}, {"gender": "Male"}]
    )
    assert [r["gender"] for r in normalize_gender(df).collect()] == [
        "Male",
        "Female",
        "Male",
    ]


# checks unknown gender values survive for quality review
def test_normalize_gender_keeps_unknown(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [{"gender": "M"}, {"gender": "Unknown"}, {"gender": None}]
    )
    out = [r["gender"] for r in normalize_gender(df).collect()]
    assert out[0] == "M"
    assert out[1] == "Unknown"
    assert out[2] is None


# checks product name splitting
def test_split_product_name(spark: SparkSession) -> None:
    df = spark.createDataFrame([{"product_name_raw": "T-Shirt | Black | S"}])
    row = split_product_name(df).collect()[0]
    assert (row["product_name"], row["color"], row["size"]) == ("T-Shirt", "Black", "S")


# checks customer cleaning end to end
def test_clean_customers(spark: SparkSession) -> None:
    schema = (
        "customer_id STRING, full_name STRING, gender STRING, phone STRING, "
        "birth_date STRING, registration_date STRING, city STRING, region STRING, "
        "loyalty_tier STRING, email STRING"
    )
    df = spark.createDataFrame(
        [
            {
                "customer_id": "a",
                "full_name": "N ",
                "gender": "MALE",
                "phone": "123",
                "birth_date": "2000-01-01",
                "registration_date": "2020-01-01",
                "city": "Cairo",
                "region": "R",
                "loyalty_tier": "Gold",
                "email": None,
            },
            {
                "customer_id": "a",
                "full_name": "N ",
                "gender": "MALE",
                "phone": "123",
                "birth_date": "2000-01-01",
                "registration_date": "2020-01-01",
                "city": "Cairo",
                "region": "R",
                "loyalty_tier": "Gold",
                "email": None,
            },
        ],
        schema=schema,
    )
    out = clean_customers(df).collect()
    assert len(out) == 1
    assert out[0]["gender"] == "Male"
    assert str(out[0]["phone"]) == "123"


# checks rows with a null natural key are dropped
def test_clean_customers_drops_null_key(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [
            {"customer_id": None, "full_name": "N", "gender": "Male", "phone": "1"},
            {"customer_id": "a", "full_name": "N", "gender": "Male", "phone": "1"},
        ]
    )
    out = clean_customers(df).collect()
    assert [r["customer_id"] for r in out] == ["a"]


# checks the null key goes before dedupe and the last duplicate wins
def test_clean_customers_null_first_dup_last(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [
            {"customer_id": None, "full_name": "Junk", "gender": "Male", "phone": "0"},
            {"customer_id": "a", "full_name": "Old", "gender": "Male", "phone": "1"},
            {"customer_id": "a", "full_name": "New", "gender": "Male", "phone": "2"},
        ]
    )
    out = clean_customers(df).collect()
    assert [r["customer_id"] for r in out] == ["a"]
    assert out[0]["full_name"] == "New"


# checks extract metadata never reaches silver
def test_drop_extract_meta(spark: SparkSession) -> None:
    df = spark.createDataFrame([{"a": 1, "loaded_at": "t"}])
    assert drop_extract_meta(df).columns == ["a"]


# checks padded payment trim and bad date coercion
def test_clean_orders(spark: SparkSession) -> None:
    schema = (
        "order_id STRING, payment_method STRING, order_status STRING, "
        "customer_id STRING, employee_id STRING, order_date STRING, loaded_at STRING"
    )
    df = spark.createDataFrame(
        [
            {
                "order_id": "o1",
                "payment_method": "  Cash  ",
                "order_status": "Completed",
                "customer_id": "c",
                "employee_id": None,
                "order_date": "not-a-date",
                "loaded_at": "t",
            }
        ],
        schema=schema,
    )
    row = clean_orders(df).collect()[0]
    assert row["payment_method"] == "Cash"
    assert row["order_date"] is None
    assert "loaded_at" not in clean_orders(df).columns


# checks union dedupes across frames
def test_union_orders(spark: SparkSession) -> None:
    a = spark.createDataFrame([{"order_id": "o1"}])
    b = spark.createDataFrame([{"order_id": "o1"}, {"order_id": "o2"}])
    assert union_orders(a, b).count() == 2


# checks returns enrichment join
def test_enrich_returns(spark: SparkSession) -> None:
    rets = spark.createDataFrame(
        [
            {
                "return_id": "r1",
                "order_id": "o1",
                "return_date": "2024-01-01",
                "return_reason": "X",
                "refund_method": "Cash",
                "return_status": "Refunded",
            }
        ]
    )
    det = spark.createDataFrame(
        [{"order_id": "o1", "product_id": "p1", "line_total_revenue": 100.0}]
    )
    row = enrich_returns(rets, det).collect()[0]
    assert row["n_items"] == 1
    assert row["order_revenue"] == 100.0


# checks returns without details are flagged not dropped
def test_enrich_returns_flags_orphan(spark: SparkSession) -> None:
    rets = spark.createDataFrame(
        [
            {
                "return_id": "r9",
                "order_id": "missing",
                "return_date": "2024-01-01",
                "return_reason": "X",
                "refund_method": "Cash",
                "return_status": "Refunded",
            }
        ]
    )
    det = spark.createDataFrame(
        [{"order_id": "o1", "product_id": "p1", "line_total_revenue": 100.0}]
    )
    rows = enrich_returns(rets, det).collect()
    assert len(rows) == 1
    assert rows[0]["return_orphan"] is True
