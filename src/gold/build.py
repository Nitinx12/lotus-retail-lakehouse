# pure builders for the gold star schema and marts
from __future__ import annotations

import pandas as pd

from src.silver.scd2 import asof_join


# resolves order facts to customer and employee versions active at order time
def build_fact_orders(
    orders: pd.DataFrame, customers: pd.DataFrame, employees: pd.DataFrame
) -> pd.DataFrame:
    out = asof_join(orders, customers, "customer_id", "customer_sk", "order_date")
    out = out.rename(columns={"customer_sk": "customer_sk"})
    emp = employees[
        ["employee_id", "employee_sk", "effective_start_date", "effective_end_date"]
    ].copy()
    emp["effective_start_date"] = pd.to_datetime(emp["effective_start_date"])
    emp["effective_end_date"] = pd.to_datetime(
        emp["effective_end_date"], errors="coerce"
    )
    out["_fdate"] = pd.to_datetime(out["order_date"])
    out = out.merge(emp, on="employee_id", how="left", suffixes=("", "_emp"))
    active = (out["effective_start_date_emp"] <= out["_fdate"]) & (
        out["effective_end_date_emp"].isna()
        | (out["_fdate"] < out["effective_end_date_emp"])
    )
    out = (
        out[active | out["employee_sk"].isna()]
        .drop(columns=["_fdate"])
        .reset_index(drop=True)
    )
    return out


# attaches customer and store keys to returns through their order
def build_fact_returns(returns: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    keys = orders[
        ["order_id", "customer_sk", "employee_sk", "store_id"]
    ].drop_duplicates("order_id")
    return returns.merge(keys, on="order_id", how="left")


# aggregates monthly revenue and cost per store
def mart_revenue_by_store_month(orders: pd.DataFrame) -> pd.DataFrame:
    out = orders.copy()
    out["month"] = pd.to_datetime(out["order_date"]).dt.to_period("M").astype(str)
    return (
        out.groupby(["store_id", "month"], as_index=False)
        .agg(
            revenue=("total_revenue", "sum"),
            cost=("total_cost", "sum"),
            orders=("order_id", "nunique"),
        )
        .sort_values(["store_id", "month"])
        .reset_index(drop=True)
    )


# computes return rate per product from details and returned order ids
def mart_return_rate_by_product(
    details: pd.DataFrame, returned_order_ids: pd.Series
) -> pd.DataFrame:
    out = details.copy()
    out["was_returned"] = out["order_id"].isin(set(returned_order_ids))
    agg = out.groupby("product_id", as_index=False).agg(
        times_ordered=("order_id", "size"), times_returned=("was_returned", "sum")
    )
    agg["return_rate"] = agg["times_returned"] / agg["times_ordered"]
    return agg.sort_values("return_rate", ascending=False).reset_index(drop=True)


# compares monthly revenue inside versus outside ramadan
def mart_ramadan_seasonality(orders: pd.DataFrame, dates: pd.DataFrame) -> pd.DataFrame:
    out = orders.merge(dates[["date_id", "is_ramadan"]], on="date_id", how="left")
    out["month"] = pd.to_datetime(out["order_date"]).dt.to_period("M").astype(str)
    return (
        out.groupby(["month", "is_ramadan"], as_index=False)
        .agg(revenue=("total_revenue", "sum"), orders=("order_id", "nunique"))
        .sort_values("month")
        .reset_index(drop=True)
    )
