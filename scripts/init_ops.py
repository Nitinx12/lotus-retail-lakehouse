# bootstraps postgres roles, databases, and the ops schema
from __future__ import annotations

import os
import uuid

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

from src.ops.db import build_dsn, read_sql

load_dotenv()


# opens an admin connection to the maintenance db
def admin_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("POSTGRES_OPS_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_OPS_PORT", "5432")),
        dbname="postgres",
        user="postgres",
        connect_timeout=5,
    )


# ensures a login role exists with the given password
def ensure_role(conn: psycopg2.extensions.connection, user: str, password: str) -> None:
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (user,))
        exists = cur.fetchone() is not None
        if not exists:
            cur.execute(
                sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(
                    sql.Identifier(user), sql.Literal(password)
                )
            )
        elif password:
            cur.execute(
                sql.SQL("ALTER ROLE {} WITH PASSWORD {}").format(
                    sql.Identifier(user), sql.Literal(password)
                )
            )


# ensures a database exists owned by the given role
def ensure_database(conn: psycopg2.extensions.connection, db: str, owner: str) -> None:
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db,))
        if cur.fetchone() is None:
            cur.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(db), sql.Identifier(owner)
                )
            )


# applies the ops ddl file and records the init run
def main() -> None:
    gold_db = os.getenv("POSTGRES_GOLD_DB", "lotus_gold_dev")
    gold_user = os.getenv("POSTGRES_GOLD_USER", "lotus_pipeline")
    gold_pw = os.getenv("POSTGRES_GOLD_PASSWORD", "")
    ops_db = os.getenv("POSTGRES_OPS_DB", "lotus_ops_dev")
    ops_user = os.getenv("POSTGRES_OPS_USER", "lotus_ops")
    ops_pw = os.getenv("POSTGRES_OPS_PASSWORD", "")
    pii_user = os.getenv("POSTGRES_PII_READER_USER", "lotus_pii_reader")
    pii_pw = os.getenv("POSTGRES_PII_READER_PASSWORD", "")

    conn = admin_conn()
    try:
        for user, pw in [(gold_user, gold_pw), (ops_user, ops_pw), (pii_user, pii_pw)]:
            ensure_role(conn, user, pw)
        ensure_database(conn, gold_db, gold_user)
        ensure_database(conn, ops_db, ops_user)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(read_sql("sql/security/roles.sql"))
    finally:
        conn.close()

    ddl = read_sql("sql/ops_schema.sql")
    ops_dsn = build_dsn(
        os.getenv("POSTGRES_OPS_HOST", "localhost"),
        int(os.getenv("POSTGRES_OPS_PORT", "5432")),
        ops_db,
        ops_user,
        ops_pw,
    )
    run_id = str(uuid.uuid4())
    with psycopg2.connect(dsn=ops_dsn, connect_timeout=5) as c:
        c.autocommit = True
        with c.cursor() as cur:
            cur.execute(ddl)
            cur.execute(
                "INSERT INTO ops.pipeline_runs (run_id, task_name, status, rows_in, rows_out) VALUES (%s, %s, %s, %s, %s)",
                (run_id, "ops_init", "success", 0, 0),
            )
    gold_dsn = build_dsn(
        os.getenv("POSTGRES_OPS_HOST", "localhost"),
        int(os.getenv("POSTGRES_OPS_PORT", "5432")),
        gold_db,
        gold_user,
        gold_pw,
    )
    with psycopg2.connect(dsn=gold_dsn, connect_timeout=5) as g:
        g.autocommit = True
        with g.cursor() as cur:
            for name in ("masked_views.sql", "grants.sql"):
                cur.execute(read_sql(f"sql/security/{name}"))
    print(f"ops ready in {ops_db} run {run_id}")


if __name__ == "__main__":
    main()
