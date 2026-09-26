"""Extract Lotus retail star-schema dataset from Kaggle and dump to MongoDB.

- Downloads/loads CSVs via kagglehub (KaggleDatasetAdapter.PANDAS)
- Creates the MongoDB database on first insert if it does not exist
  (MongoDB creates DBs lazily -- no explicit CREATE DATABASE needed)
- Adds a `loaded_at` UTC timestamp to every document
"""
import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient

import kagglehub
from kagglehub import KaggleDatasetAdapter

load_dotenv()

DATASET = "abdelrahmanmahmoud22/lotus-group-retail-star-schema-bi"
DEFAULT_MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DEFAULT_MONGO_DB = os.getenv("MONGO_DB", "lotus_retail")


def get_client(uri: str) -> MongoClient:
    client: MongoClient = MongoClient(uri, serverSelectionTimeoutMS=5000)
    # Fail fast if Mongo is unreachable
    client.admin.command("ping")
    return client


def ensure_db(client: MongoClient, db_name: str):
    """Return handle to db, creating it implicitly if needed.

    MongoDB has no CREATE DATABASE -- a DB appears in
    list_database_names() only after it holds at least one collection
    with data. So we just check existence for logging; the first
    insert creates it.
    """
    existing = client.list_database_names()
    if db_name not in existing:
        print(f"Database '{db_name}' does not exist yet -- it will be created on first insert.")
    else:
        print(f"Database '{db_name}' already exists -- reusing it.")
    return client[db_name]


def clean_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to Mongo-safe dicts (NaN/NaT -> None)."""
    df = df.where(pd.notnull(df), None)
    # Extra pass: pandas may leave NaT in datetime cols
    records = df.to_dict(orient="records")
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, float) and pd.isna(v):
                rec[k] = None
            elif v is pd.NaT:
                rec[k] = None
    return records


def discover_files(dataset: str) -> list[str]:
    """Download dataset cache dir and list loadable data files."""
    local_dir = Path(kagglehub.dataset_download(dataset))
    print(f"Dataset cached at: {local_dir}")
    files = sorted(
        p.name
        for p in local_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".csv", ".parquet", ".xlsx", ".xls"}
    )
    print(f"Discovered files: {files}")
    return files


def load_file(dataset: str, file_path: str) -> pd.DataFrame:
    """Load a single dataset file via the PANDAS adapter."""
    df: pd.DataFrame = kagglehub.load_dataset(
        KaggleDatasetAdapter.PANDAS,
        dataset,
        file_path,
    )
    return df


def collection_name_for(file_path: str) -> str:
    stem = Path(file_path).stem.strip().lower().replace(" ", "_").replace("-", "_")
    return stem or "unknown"


def dump_df(db, df: pd.DataFrame, collection: str, drop: bool = False) -> int:
    loaded_at = datetime.now(timezone.utc)
    records = clean_records(df)
    for rec in records:
        rec["loaded_at"] = loaded_at
    coll = db[collection]
    if drop:
        coll.drop()
    if not records:
        print(f"[{collection}] no rows -- skipping insert.")
        return 0
    # insert in chunks to avoid 16MB / batch limits on big tables
    total = 0
    for i in range(0, len(records), 5000):
        chunk = records[i : i + 5000]
        res = coll.insert_many(chunk, ordered=False)
        total += len(res.inserted_ids)
    print(f"[{collection}] inserted {total} docs (loaded_at={loaded_at.isoformat()}).")
    return total


def main() -> None:
    ap = argparse.ArgumentParser(description="Kaggle -> MongoDB loader with loaded_at timestamp")
    ap.add_argument("--dataset", default=DATASET)
    ap.add_argument(
        "--file",
        default="",
        help="Single file inside the dataset (e.g. 'Fact_Sales.csv'). "
        "If empty, all discovered CSV/Parquet/Excel files are loaded.",
    )
    ap.add_argument("--mongo-uri", default=DEFAULT_MONGO_URI)
    ap.add_argument("--mongo-db", default=DEFAULT_MONGO_DB)
    ap.add_argument("--drop", action="store_true", help="Drop each collection before loading")
    args = ap.parse_args()

    client = get_client(args.mongo_uri)
    db = ensure_db(client, args.mongo_db)

    targets = [args.file] if args.file else discover_files(args.dataset)
    if not targets:
        raise SystemExit("No data files found in dataset.")

    grand_total = 0
    for f in targets:
        print(f"Loading {f} ...")
        df = load_file(args.dataset, f)
        print(f"  rows={len(df)} cols={list(df.columns)}")
        print("  First 5 records:")
        print(df.head().to_string())
        grand_total += dump_df(db, df, collection_name_for(f), drop=args.drop)

    print(f"Done. Total docs inserted: {grand_total} into db '{args.mongo_db}'.")


if __name__ == "__main__":
    main()
