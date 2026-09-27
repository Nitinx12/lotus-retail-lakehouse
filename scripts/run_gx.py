# runs great expectations checkpoints into ops
from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from pathlib import Path

import great_expectations as gx
import psycopg2
from dotenv import load_dotenv

from src.ops.db import build_dsn, finish_run, start_run
from src.quality.gx_suites import layer_plan, score_checkpoint

load_dotenv()

DATA_DIR = Path("data")
LOG_FILE = Path("logs/gx.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger("gx")


# opens the ops postgres store
def ops_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        dsn=build_dsn(
            os.getenv("POSTGRES_OPS_HOST", "localhost"),
            int(os.getenv("POSTGRES_OPS_PORT", "5432")),
            os.getenv("POSTGRES_OPS_DB", "lotus_ops_dev"),
            os.getenv("POSTGRES_OPS_USER", "lotus_ops"),
            os.getenv("POSTGRES_OPS_PASSWORD", ""),
        ),
        connect_timeout=5,
    )


# runs one layer checkpoint and returns pass percent with failures
def run_checkpoint(layer: str) -> tuple[float, int]:
    context = gx.get_context(mode="ephemeral")
    source = context.data_sources.add_pandas_filesystem(
        f"lotus_{layer}", base_directory=str(DATA_DIR / layer)
    )
    definitions = []
    for pos, (filename, checks) in enumerate(layer_plan(layer).items()):
        asset = source.add_parquet_asset(f"{layer}_{pos}")
        batch = asset.add_batch_definition_path(f"batch_{pos}", path=filename)
        suite = gx.ExpectationSuite(name=f"gx_{layer}_{pos}")
        for check in checks:
            suite.add_expectation(check)
        definition = gx.ValidationDefinition(
            data=batch, suite=suite, name=f"gx_{layer}_{pos}"
        )
        context.suites.add(suite)
        context.validation_definitions.add(definition)
        definitions.append(definition)
    checkpoint = gx.Checkpoint(name=f"gx_{layer}", validation_definitions=definitions)
    context.checkpoints.add(checkpoint)
    result = checkpoint.run()
    return score_checkpoint(result.run_results)


# runs the requested suite and blocks on failure
def main() -> None:
    parser = argparse.ArgumentParser(description="great expectations checkpoint runner")
    parser.add_argument("--suite", choices=["bronze", "silver", "gold"], required=True)
    args = parser.parse_args()
    run_id = str(uuid.uuid4())
    task = f"gx_{args.suite}"
    log.info("gx start suite=%s run=%s", args.suite, run_id)
    with ops_conn() as ops:
        ops.autocommit = True
        with ops.cursor() as cur:
            start_run(cur, run_id, task)
            try:
                pct, failed = run_checkpoint(args.suite)
                cur.execute(
                    "INSERT INTO ops.quality_results "
                    "(run_id, suite_name, success_percent, failed_expectations) "
                    "VALUES (%s, %s, %s, %s)",
                    (run_id, task, pct, failed),
                )
                finish_run(
                    cur, run_id, task, "failed" if failed else "success", 0, failed
                )
            except Exception as exc:
                ops.rollback()
                finish_run(cur, run_id, task, "failed", 0, 0, str(exc))
                ops.commit()
                raise
    print(f"gx done suite={args.suite} run={run_id} failed={failed}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
