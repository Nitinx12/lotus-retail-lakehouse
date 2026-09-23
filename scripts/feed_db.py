"""
scripts/feed_db.py
==================
Utility to load raw booking data into Postgres and MongoDB.
Uses src.utils.connection for DB access and src.utils.logger for logging.
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path for `src.` imports when run directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.logger import get_logger
from src.utils.connection import get_postgres_engine, get_mongo_db

log = get_logger("feed_db")


def main(limit: int | None = None) -> None:
    """Load data into Postgres and MongoDB."""
    log.info("Starting feed_db: limit=%s", limit)

    # Postgres example - verifies connection
    try:
        engine = get_postgres_engine()
        log.info("Postgres engine ready: %s", engine.url)
        # TODO: implement CSV loading into bronze schema
    except Exception:
        log.exception("Postgres connection failed")
        raise

    # MongoDB example - verifies connection
    try:
        db = get_mongo_db()
        log.info("MongoDB connected: db=%s collections=%s", db.name, db.list_collection_names())
    except Exception:
        log.exception("MongoDB connection failed")
        raise

    log.info("feed_db completed successfully")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Feed raw data into databases")
    parser.add_argument("--limit", type=int, default=None, help="Limit rows to load")
    args = parser.parse_args()
    main(limit=args.limit)
