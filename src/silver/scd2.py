# slowly changing dimension type 2 versioning
from __future__ import annotations

import hashlib

import pandas as pd

HASH_COL = "attribute_hash"

# tracked attributes per ARCHITECTURE section 7
CUSTOMER_TRACKED = ["region", "loyalty_tier"]
EMPLOYEE_TRACKED = ["store_id", "role"]


# hashes tracked attributes into one comparable string
def attribute_hash(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    return (
        df[cols]
        .astype("string")
        .fillna("")
        .agg("|".join, axis=1)
        .map(lambda s: hashlib.md5(s.encode()).hexdigest())
    )


# merges incoming rows into a versioned scd2 table
def apply_scd2(
    current: pd.DataFrame | None,
    incoming: pd.DataFrame,
    natural_key: str,
    tracked: list[str],
    sk_col: str,
    business_date: str,
) -> pd.DataFrame:
    fresh = incoming.drop_duplicates(subset=[natural_key], keep="last").copy()
    fresh[HASH_COL] = attribute_hash(fresh, tracked).values
    if current is None or current.empty:
        out = fresh.copy()
        out[sk_col] = range(1, len(out) + 1)
        out["effective_start_date"] = business_date
        out["effective_end_date"] = None
        out["is_current"] = True
        return out.reset_index(drop=True)
    table = current.copy()
    max_sk = int(table[sk_col].max())
    cur = table[table["is_current"]].set_index(natural_key)
    dupes = cur.index[cur.index.duplicated()].unique().tolist()
    if dupes:
        raise ValueError(
            f"scd2 {natural_key} has several current rows "
            f"for keys={dupes[:5]} count={len(dupes)}"
        )
    for _, row in fresh.iterrows():
        key = row[natural_key]
        if key not in cur.index:
            max_sk += 1
            new = row.to_dict()
            new.update(
                {
                    sk_col: max_sk,
                    "effective_start_date": business_date,
                    "effective_end_date": None,
                    "is_current": True,
                }
            )
            table = pd.concat([table, pd.DataFrame([new])], ignore_index=True)
        elif cur.loc[key, HASH_COL] != row[HASH_COL]:
            table.loc[
                (table[natural_key] == key) & (table["is_current"]),
                ["effective_end_date", "is_current"],
            ] = [business_date, False]
            max_sk += 1
            new = row.to_dict()
            new.update(
                {
                    sk_col: max_sk,
                    "effective_start_date": business_date,
                    "effective_end_date": None,
                    "is_current": True,
                }
            )
            table = pd.concat([table, pd.DataFrame([new])], ignore_index=True)
    return table.reset_index(drop=True)


# joins facts to the dimension version active on the fact date
def asof_join(
    facts: pd.DataFrame,
    dim: pd.DataFrame,
    natural_key: str,
    sk_col: str,
    fact_date_col: str,
) -> pd.DataFrame:
    dim = dim.copy()
    dim["effective_start_date"] = pd.to_datetime(dim["effective_start_date"])
    dim["effective_end_date"] = pd.to_datetime(
        dim["effective_end_date"], errors="coerce"
    )
    facts = facts.copy()
    facts["_fdate"] = pd.to_datetime(facts[fact_date_col], errors="coerce")
    facts["_pos"] = range(len(facts))
    merged = facts.merge(dim, on=natural_key, how="left", suffixes=("", "_dim"))
    active = (merged["effective_start_date"] <= merged["_fdate"]) & (
        merged["effective_end_date"].isna()
        | (merged["_fdate"] < merged["effective_end_date"])
    )
    matched = merged[active].drop(columns=["_fdate"])
    missing = facts[~facts["_pos"].isin(matched["_pos"])]
    fill = missing.drop(columns=["_fdate", "_pos"]).merge(
        dim.iloc[0:0], on=natural_key, how="left", suffixes=("", "_dim")
    )
    return pd.concat(
        [matched.drop(columns=["_pos"]), fill], ignore_index=True
    ).reset_index(drop=True)
