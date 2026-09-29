# lists every table plus column in the postgres gold schema
from __future__ import annotations

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text

load_dotenv()


# opens the gold serving warehouse for reads
def gold_engine() -> Engine:
    return create_engine(
        "postgresql+psycopg2://"
        f"{os.getenv('POSTGRES_GOLD_USER', 'lotus_pipeline')}"
        f":{os.getenv('POSTGRES_GOLD_PASSWORD', '')}"
        f"@{os.getenv('POSTGRES_GOLD_HOST', 'localhost')}"
        f":{os.getenv('POSTGRES_GOLD_PORT', '5432')}"
        f"/{os.getenv('POSTGRES_GOLD_DB', 'lotus_gold_dev')}",
        connect_args={"connect_timeout": 5},
    )


# prints gold tables with columns from information_schema
def main() -> None:
    query = text(
        "SELECT table_name, column_name, data_type "
        "FROM information_schema.columns "
        "WHERE table_schema = 'gold' "
        "ORDER BY table_name, ordinal_position"
    )
    with gold_engine().connect() as conn:
        df = pd.read_sql(query, conn)
    if df.empty:
        print(
            "No tables found in the gold schema, check POSTGRES_GOLD_DB in .env and run publish first"
        )
        return
    for table_name, group in df.groupby("table_name"):
        print(f"\n{table_name}")
        print("-" * len(str(table_name)))
        for _, row in group.iterrows():
            print(f"  {row['column_name']:<30} {row['data_type']}")


if __name__ == "__main__":
    main()
