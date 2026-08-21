"""
Incremental CSV -> PostgreSQL loader
=====================================
Loads Bookings.csv into Postgres. "Incremental" is enforced on the
Booking_ID column: it's used as the table's PRIMARY KEY, and every load
runs an INSERT ... ON CONFLICT (Booking_ID) DO NOTHING, so:

  - Rows whose Booking_ID is already in the table are skipped.
  - Only genuinely new Booking_IDs get inserted.
  - You can re-run this script (e.g. daily/hourly on a refreshed CSV)
    and it will never duplicate data.

BUGFIX (2026-08-21): previously the CSV was read with
pd.read_csv(..., chunksize=CHUNK_SIZE), which makes pandas infer each
chunk's column dtypes independently. A sparsely-populated column (e.g.
"Time") could come back as float64 in one chunk (all-NaN in that
chunk -> DOUBLE PRECISION) and object in another (real "HH:MM:SS"
strings -> TEXT), so the staging table's type could disagree with the
already-created target table's type on any given run, causing
psycopg2.errors.DatatypeMismatch on INSERT ... SELECT.

Fix: the CSV is now read ONCE in full to settle on a single, stable
dtype per column (pandas reconciles types across the whole column when
there's no chunksize), and that schema is used consistently for both
the staging table and the target table. If the target table already
exists with a drifted column type (e.g. from a prior run hitting this
bug), ensure_tables() automatically reconciles it via ALTER COLUMN
before loading, instead of failing. CHUNK_SIZE now only controls how
many rows are staged/upserted per DB round trip -- it no longer
affects CSV parsing/dtype inference.

For very large CSVs (multi-GB) where loading the whole file into
memory at once isn't feasible, swap get_canonical_schema()/the in-memory
slicing loop for a dtype-pinned chunksize read instead (determine the
schema once as below, then pass that same dtype= dict into every
pd.read_csv(..., chunksize=...) call).

Config comes from a .env file next to this script:
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DATABASE,
    POSTGRES_USERNAME, POSTGRES_PASSWORD
    CSV_FILE_PATH   - path to Bookings.csv
    TABLE_NAME      - target table (default: bookings)
    CHUNK_SIZE      - rows per insert batch (default: 5000)

Run:
    pip install -r requirements.txt
    python incremental_load.py
"""

import os
import sys
import time

# Make sure the project root (parent of this script's folder) is importable,
# so `utils/` resolves correctly no matter where this script is run from.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import BIGINT, DOUBLE_PRECISION, BOOLEAN, TIMESTAMP, TEXT
from dotenv import load_dotenv

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    MofNCompleteColumn,
    TimeElapsedColumn,
)

from utils.logger import get_logger

load_dotenv()
console = Console()

# ---------------- Config ----------------
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_DB = os.getenv("POSTGRES_DATABASE", "postgres")
PG_USER = os.getenv("POSTGRES_USERNAME", "postgres")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "")

CSV_FILE_PATH = os.getenv(
    "CSV_FILE_PATH",
    r"C:\Users\91852\OneDrive\Desktop\Github Repo\Booking_data\datasets\data\Bookings.csv",
)
TABLE_NAME = os.getenv("TABLE_NAME", "bookings")
KEY_COLUMN = "Booking_ID"  # must match the CSV header exactly (after sanitizing)
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "5000"))
LOG_TABLE = "etl_load_log"

log = get_logger("incremental_loader")

# Single source of truth for pandas dtype -> Postgres type, used both for
# raw DDL (CREATE TABLE / ALTER COLUMN) and for pandas' to_sql(dtype=...),
# so the staging table and the target table can never disagree.
TYPE_INFO = {
    "int64": {"pg": "BIGINT", "sa": BIGINT},
    "float64": {"pg": "DOUBLE PRECISION", "sa": DOUBLE_PRECISION},
    "bool": {"pg": "BOOLEAN", "sa": BOOLEAN},
    "datetime64[ns]": {"pg": "TIMESTAMP", "sa": TIMESTAMP},
    "object": {"pg": "TEXT", "sa": TEXT},
}
DEFAULT_TYPE = TYPE_INFO["object"]  # fall back to TEXT for any dtype we don't recognize

# Normalizes what Postgres reports back in information_schema.columns to
# the same vocabulary as TYPE_INFO["pg"], so we can compare "is this
# column already the right type" without string-format mismatches.
PG_DATA_TYPE_NORMALIZE = {
    "bigint": "BIGINT",
    "integer": "BIGINT",
    "smallint": "BIGINT",
    "double precision": "DOUBLE PRECISION",
    "real": "DOUBLE PRECISION",
    "numeric": "DOUBLE PRECISION",
    "boolean": "BOOLEAN",
    "timestamp without time zone": "TIMESTAMP",
    "timestamp with time zone": "TIMESTAMP",
    "text": "TEXT",
    "character varying": "TEXT",
}


def get_engine():
    url = f"postgresql+psycopg2://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    return create_engine(url)


def sanitize_columns(columns):
    """Make CSV headers safe/consistent Postgres column names."""
    return [c.strip().replace(" ", "_") for c in columns]


def get_canonical_schema(csv_path):
    """
    Read the ENTIRE CSV once (no chunksize) purely to settle on a single,
    stable dtype per column for this run. When there's no chunksize,
    pandas infers each column's dtype from the whole file, so this can
    never disagree with itself the way per-chunk inference can.
    Returns {sanitized_column_name: pandas_dtype_string}.
    """
    console.print("[dim]Scanning CSV once to determine a consistent column schema...[/dim]")
    full_df = pd.read_csv(csv_path, low_memory=False)
    full_df.columns = sanitize_columns(full_df.columns)
    schema = {col: str(dtype) for col, dtype in full_df.dtypes.items()}
    return full_df, schema


def get_existing_column_types(engine, table_name):
    sql = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = :t
    """
    with engine.begin() as conn:
        rows = conn.execute(text(sql), {"t": table_name}).fetchall()
    return {r.column_name: r.data_type for r in rows}


def reconcile_schema(engine, table_name, schema):
    """
    Self-heal: if the target table already exists with a column type that
    doesn't match the canonical schema (e.g. left over from a previous run
    that hit the chunk-dtype-drift bug), ALTER it into line rather than
    letting the INSERT ... SELECT fail with a cryptic DatatypeMismatch.
    """
    existing = get_existing_column_types(engine, table_name)
    if not existing:
        return  # table didn't exist before this run; nothing to reconcile

    fixes = []
    for col, dtype in schema.items():
        if col not in existing:
            continue  # new column introduced by this CSV; handled separately if needed
        desired_pg = TYPE_INFO.get(dtype, DEFAULT_TYPE)["pg"]
        current_pg = PG_DATA_TYPE_NORMALIZE.get(existing[col].lower(), existing[col].upper())
        if current_pg != desired_pg:
            fixes.append((col, current_pg, desired_pg))

    if not fixes:
        return

    table = Table(title=f'Reconciling drifted column types on "{table_name}"', show_lines=False)
    table.add_column("Column", style="bold")
    table.add_column("Was")
    table.add_column("Now")
    for col, before, after in fixes:
        table.add_row(col, before, after)
    console.print(table)
    log.warning(f"Reconciling {len(fixes)} drifted column type(s) on \"{table_name}\": {fixes}")

    with engine.begin() as conn:
        for col, before, after in fixes:
            alter_sql = (
                f'ALTER TABLE "{table_name}" ALTER COLUMN "{col}" '
                f'TYPE {after} USING "{col}"::{after};'
            )
            try:
                conn.execute(text(alter_sql))
            except Exception as exc:
                console.print(
                    Panel(
                        f'Could not automatically convert column "{col}" on '
                        f'"{table_name}" from {before} to {after}.\n'
                        f"Underlying error: {exc}\n\n"
                        f'Fix manually, e.g.: {alter_sql}',
                        title="Schema reconciliation failed",
                        border_style="red",
                    )
                )
                log.error(f"Schema reconciliation failed for column {col}: {exc}")
                sys.exit(1)


def ensure_tables(engine, schema):
    if KEY_COLUMN not in schema:
        log.error(f"Key column '{KEY_COLUMN}' not found in CSV columns: {list(schema.keys())}")
        sys.exit(1)

    cols_sql = [f'"{col}" {TYPE_INFO.get(dtype, DEFAULT_TYPE)["pg"]}' for col, dtype in schema.items()]
    create_sql = f'''
        CREATE TABLE IF NOT EXISTS "{TABLE_NAME}" (
            {", ".join(cols_sql)},
            _loaded_at TIMESTAMP DEFAULT now(),
            PRIMARY KEY ("{KEY_COLUMN}")
        );
    '''
    log_sql = f'''
        CREATE TABLE IF NOT EXISTS "{LOG_TABLE}" (
            id SERIAL PRIMARY KEY,
            run_at TIMESTAMP DEFAULT now(),
            rows_read INTEGER,
            rows_inserted INTEGER,
            rows_skipped INTEGER,
            source_file TEXT
        );
    '''
    with engine.begin() as conn:
        conn.execute(text(create_sql))
        conn.execute(text(log_sql))

    # Whether the table was just created (no-op below) or already existed
    # (possibly with drifted types from a prior bad run), make sure it now
    # matches the canonical schema before we try to insert into it.
    reconcile_schema(engine, TABLE_NAME, schema)


def get_row_count(engine, table_name):
    """Returns current row count of a table, or 0 if it doesn't exist yet."""
    check_sql = "SELECT to_regclass(:t)"
    with engine.begin() as conn:
        exists = conn.execute(text(check_sql), {"t": table_name}).scalar()
        if exists is None:
            return 0
        return conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()


def load_incremental(engine, csv_path):
    df, schema = get_canonical_schema(csv_path)
    ensure_tables(engine, schema)

    sa_dtypes = {col: TYPE_INFO.get(dtype, DEFAULT_TYPE)["sa"] for col, dtype in schema.items()}
    col_list = ", ".join(f'"{c}"' for c in df.columns)
    staging_table = f"_staging_{TABLE_NAME}"

    total_read = len(df)
    total_inserted = 0

    progress_columns = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("rows"),
        TimeElapsedColumn(),
    ]
    with Progress(*progress_columns, console=console) as progress:
        task = progress.add_task("Loading chunks", total=total_read)
        for start in range(0, total_read, CHUNK_SIZE):
            chunk = df.iloc[start:start + CHUNK_SIZE]

            # dtype= pins the staging table to the exact same types as the
            # (now-reconciled) target table, so this can't drift again.
            chunk.to_sql(staging_table, engine, if_exists="replace", index=False, dtype=sa_dtypes)

            upsert_sql = f'''
                INSERT INTO "{TABLE_NAME}" ({col_list})
                SELECT {col_list} FROM "{staging_table}"
                ON CONFLICT ("{KEY_COLUMN}") DO NOTHING;
            '''
            with engine.begin() as conn:
                result = conn.execute(text(upsert_sql))
                inserted = result.rowcount or 0
                total_inserted += inserted
                conn.execute(text(f'DROP TABLE IF EXISTS "{staging_table}"'))

            log.info(f"Chunk done: read={len(chunk)}, newly_inserted={inserted}")
            progress.update(task, advance=len(chunk))

    return total_read, total_inserted, total_read - total_inserted


def log_run(engine, rows_read, rows_inserted, rows_skipped, source_file):
    with engine.begin() as conn:
        conn.execute(
            text(f'''
                INSERT INTO "{LOG_TABLE}" (rows_read, rows_inserted, rows_skipped, source_file)
                VALUES (:r, :i, :s, :f)
            '''),
            {"r": rows_read, "i": rows_inserted, "s": rows_skipped, "f": source_file},
        )


def print_summary(previous_count, rows_read, rows_inserted, rows_skipped, new_count, duration):
    table = Table(title="Load Summary", show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan", justify="right")
    table.add_column()
    table.add_row("Table", TABLE_NAME)
    table.add_row("Rows in table before", str(previous_count))
    table.add_row("Rows read from CSV", str(rows_read))
    table.add_row("Rows newly inserted", f"[bold green]{rows_inserted}[/bold green]")
    table.add_row("Rows skipped (dupes)", str(rows_skipped))
    table.add_row("Rows in table after", str(new_count))
    table.add_row("Duration", f"{duration:.2f} sec")
    console.print(Panel(table, border_style="cyan"))

    log.info(
        f"LOAD SUMMARY table={TABLE_NAME} previous={previous_count} read={rows_read} "
        f"inserted={rows_inserted} skipped={rows_skipped} after={new_count} duration={duration:.2f}s"
    )


def main():
    if not os.path.exists(CSV_FILE_PATH):
        log.error(f"CSV file not found: {CSV_FILE_PATH}")
        console.print(f"[bold red]CSV file not found:[/bold red] {CSV_FILE_PATH}")
        sys.exit(1)

    console.print(Panel(f"[bold]{CSV_FILE_PATH}[/bold] -> table [bold]\"{TABLE_NAME}\"[/bold]",
                         title="Incremental CSV -> PostgreSQL Loader", border_style="cyan"))
    log.info(f"Starting incremental load: {CSV_FILE_PATH} -> table '{TABLE_NAME}'")
    engine = get_engine()

    start_time = time.time()
    previous_count = get_row_count(engine, TABLE_NAME)

    rows_read, rows_inserted, rows_skipped = load_incremental(engine, CSV_FILE_PATH)
    log_run(engine, rows_read, rows_inserted, rows_skipped, CSV_FILE_PATH)

    new_count = get_row_count(engine, TABLE_NAME)
    duration = time.time() - start_time

    log.info(
        f"Finished. rows_read={rows_read}, newly_inserted={rows_inserted}, "
        f"already_existed/skipped={rows_skipped}"
    )
    print_summary(previous_count, rows_read, rows_inserted, rows_skipped, new_count, duration)


if __name__ == "__main__":
    main()