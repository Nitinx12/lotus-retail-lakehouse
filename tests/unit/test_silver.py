# unit tests for silver cleaning transforms
import pandas as pd

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
def test_dedupe() -> None:
    df = pd.DataFrame([{"id": "a", "v": 1}, {"id": "a", "v": 2}])
    assert len(dedupe(df, ["id"])) == 1


# checks whitespace stripping
def test_strip_text() -> None:
    df = pd.DataFrame([{"p": "  Cash  "}])
    assert strip_text(df, ["p"])["p"].iloc[0] == "Cash"


# checks gender variants collapse
def test_normalize_gender() -> None:
    df = pd.DataFrame([{"gender": "MALE"}, {"gender": "female"}, {"gender": "Male"}])
    assert normalize_gender(df)["gender"].tolist() == ["Male", "Female", "Male"]


# checks unknown gender values survive for quality review
def test_normalize_gender_keeps_unknown() -> None:
    df = pd.DataFrame([{"gender": "M"}, {"gender": "Unknown"}, {"gender": None}])
    out = normalize_gender(df)["gender"].tolist()
    assert out[0] == "M"
    assert out[1] == "Unknown"
    assert pd.isna(out[2])


# checks product name splitting
def test_split_product_name() -> None:
    df = pd.DataFrame([{"product_name_raw": "T-Shirt | Black | S"}])
    out = split_product_name(df)
    assert (out["product_name"].iloc[0], out["color"].iloc[0], out["size"].iloc[0]) == (
        "T-Shirt",
        "Black",
        "S",
    )


# checks customer cleaning end to end
def test_clean_customers() -> None:
    df = pd.DataFrame(
        [
            {
                "customer_id": "a",
                "full_name": "N ",
                "gender": "MALE",
                "phone": 123,
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
                "phone": 123,
                "birth_date": "2000-01-01",
                "registration_date": "2020-01-01",
                "city": "Cairo",
                "region": "R",
                "loyalty_tier": "Gold",
                "email": None,
            },
        ]
    )
    out = clean_customers(df)
    assert len(out) == 1
    assert out["gender"].iloc[0] == "Male"
    assert str(out["phone"].iloc[0]) == "123"


# checks rows with a null natural key are dropped
def test_clean_customers_drops_null_key() -> None:
    df = pd.DataFrame(
        [
            {"customer_id": None, "full_name": "N", "gender": "Male", "phone": "1"},
            {"customer_id": "a", "full_name": "N", "gender": "Male", "phone": "1"},
        ]
    )
    out = clean_customers(df)
    assert out["customer_id"].tolist() == ["a"]


# checks extract metadata never reaches silver
def test_drop_extract_meta() -> None:
    df = pd.DataFrame([{"a": 1, "loaded_at": "t"}])
    out = drop_extract_meta(df)
    assert list(out.columns) == ["a"]


# checks padded payment trim and bad date coercion
def test_clean_orders() -> None:
    df = pd.DataFrame(
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
        ]
    )
    out = clean_orders(df)
    assert out["payment_method"].iloc[0] == "Cash"
    assert pd.isna(out["order_date"].iloc[0])
    assert "loaded_at" not in out.columns


# checks union dedupes across frames
def test_union_orders() -> None:
    a = pd.DataFrame([{"order_id": "o1"}])
    b = pd.DataFrame([{"order_id": "o1"}, {"order_id": "o2"}])
    assert len(union_orders(a, b)) == 2


# checks returns enrichment join
def test_enrich_returns() -> None:
    rets = pd.DataFrame(
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
    det = pd.DataFrame(
        [{"order_id": "o1", "product_id": "p1", "line_total_revenue": 100.0}]
    )
    out = enrich_returns(rets, det)
    assert out["n_items"].iloc[0] == 1
    assert out["order_revenue"].iloc[0] == 100.0


# checks returns without details are flagged not dropped
def test_enrich_returns_flags_orphan() -> None:
    rets = pd.DataFrame(
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
    det = pd.DataFrame(
        [{"order_id": "o1", "product_id": "p1", "line_total_revenue": 100.0}]
    )
    out = enrich_returns(rets, det)
    assert len(out) == 1
    assert bool(out["return_orphan"].iloc[0]) is True
