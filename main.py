# single entrypoint dispatching pipeline stages as subprocesses
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

STAGES: dict[str, list[str]] = {
    "initops": ["scripts/init_ops.py"],
    "sql-ops": ["scripts/run_sql.py", "--db", "ops"],
    "sql-gold": ["scripts/run_sql.py", "--db", "gold"],
    "extract": ["scripts/extract_to_mongo.py"],
    "plpgsql-source": ["scripts/run_plpgsql.py", "--suite", "source"],
    "bronze": ["scripts/run_bronze.py"],
    "silver": ["scripts/run_silver.py"],
    "scd2": ["scripts/run_scd2.py"],
    "gold": ["scripts/run_gold.py"],
    "quality": ["scripts/run_quality.py"],
    "gx-bronze": ["scripts/run_gx.py", "--suite", "bronze"],
    "gx-silver": ["scripts/run_gx.py", "--suite", "silver"],
    "gx-gold": ["scripts/run_gx.py", "--suite", "gold"],
    "publish": ["scripts/run_publish.py"],
    "plpgsql-gold": ["scripts/run_plpgsql.py", "--suite", "gold"],
}

EXPANSIONS: dict[str, list[str]] = {
    "gx": ["gx-bronze", "gx-silver", "gx-gold"],
    "all": [
        "sql-ops",
        "plpgsql-source",
        "bronze",
        "silver",
        "scd2",
        "gold",
        "quality",
        "sql-gold",
        "publish",
        "plpgsql-gold",
    ],
}


# build the stage argument parser
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lotus pipeline entrypoint")
    parser.add_argument("stages", nargs="*", help="stage names or all")
    parser.add_argument("--list", action="store_true", help="list stages")
    return parser


# expand group names into concrete stage names
def expand(names: list[str]) -> list[str]:
    out: list[str] = []
    for name in names:
        out.extend(EXPANSIONS.get(name, [name]))
    return out


# run one stage script and return its exit code
def run_stage(name: str) -> int:
    if name not in STAGES:
        print(f"unknown stage: {name}", file=sys.stderr)
        return 2
    env = dict(os.environ)
    root = str(Path(__file__).resolve().parent)
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run([sys.executable, *STAGES[name]], check=False, env=env)
    return proc.returncode


# run stages in order stopping on first failure
def run_many(names: list[str]) -> int:
    for name in expand(names):
        code = run_stage(name)
        if code != 0:
            return code
    return 0


# dispatch cli args to stages
def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list:
        for name in [*STAGES, *EXPANSIONS]:
            print(name)
        return 0
    if not args.stages:
        print("pass stage names or all, see --list", file=sys.stderr)
        return 2
    return run_many(args.stages)


if __name__ == "__main__":
    raise SystemExit(main())
