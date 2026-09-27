# pure cleaning transforms for the silver layer
from __future__ import annotations

import pandas as pd


# drops duplicate rows on the natural key keeping the first
def dedupe(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    return df.drop_duplicates(subset=keys, keep="first").reset_index(drop=True)


# strips surrounding whitespace on the given string columns
def strip_text(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = out[c].where(out[c].isna(), out[c].astype(str).str.strip())
    return out


# title cases gender variants into Male and Female
def normalize_gender(df: pd.DataFrame, col: str = "gender") -> pd.DataFrame:
    out = df.copy()
    if col in out.columns:
        stripped = out[col].where(out[col].isna(), out[col].astype(str).str.strip())
        mapped = stripped.where(
            stripped.isna(),
            stripped.str.lower().map({"male": "Male", "female": "Female"}),
        )
        out[col] = mapped.fillna(stripped)
    return out


# cleans dim_customers fixing dupes, case, phone type, and dates
def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    out = dedupe(df, ["customer_id"])
    out = out[out["customer_id"].notna() & (out["customer_id"] != "")]
    out = strip_text(out, ["full_name", "city", "region", "loyalty_tier", "email"])
    out = normalize_gender(out)
    out["phone"] = out["phone"].astype("string")
    for c in ("birth_date", "registration_date"):
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors="coerce").dt.date
    return out


# splits pipe separated product names into name, color, and size
def split_product_name(df: pd.DataFrame, col: str = "product_name_raw") -> pd.DataFrame:
    out = df.copy()
    parts = out[col].astype(str).str.split("|", n=2, expand=True)
    out["product_name"] = parts[0].str.strip()
    out["color"] = parts[1].str.strip() if parts.shape[1] > 1 else None
    out["size"] = parts[2].str.strip() if parts.shape[1] > 2 else None
    return out.drop(columns=[col])


# cleans dim_products splitting names and dropping the redundant price text
def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    out = dedupe(df, ["product_id"])
    out = strip_text(out, ["category", "subcategory", "brand"])
    out = split_product_name(out)
    return out.drop(columns=["unit_price_text"], errors="ignore")


# cleans one fact_orders frame trimming text and parsing dates
def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    out = strip_text(
        df, ["payment_method", "order_status", "customer_id", "employee_id", "order_id"]
    )
    out["employee_id"] = out["employee_id"].where(
        out["employee_id"].notna() & (out["employee_id"] != ""), None
    )
    out = out[out["order_id"].notna() & (out["order_id"] != "")]
    out["order_date"] = pd.to_datetime(out["order_date"], errors="coerce").dt.date
    return out.reset_index(drop=True)


# unions the two orders frames into one deduplicated frame
def union_orders(first: pd.DataFrame, second: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat([first, second], ignore_index=True)
    return dedupe(combined, ["order_id"])


# enriches returns with per order item count and revenue from details
def enrich_returns(returns: pd.DataFrame, details: pd.DataFrame) -> pd.DataFrame:
    agg = details.groupby("order_id", as_index=False).agg(
        n_items=("product_id", "size"), order_revenue=("line_total_revenue", "sum")
    )
    out = returns.merge(agg, on="order_id", how="left")
    out["return_orphan"] = out["n_items"].isna()
    out["return_date"] = pd.to_datetime(out["return_date"], errors="coerce").dt.date
    return strip_text(out, ["return_reason", "refund_method", "return_status"])
