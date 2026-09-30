# AGENTS.md

Instructions for any AI coding agent working in this repo (Lotus Retail Lakehouse). Keep changes small and follow these exactly, they are not suggestions.

## Setup

- Python via `uv` only. No pip, no poetry, no conda. `uv sync` to install, `uv run <cmd>` to execute.
- Copy `.env.example` to `.env` for local secrets. Never commit `.env`.
- Windows local runs go through the PowerShell scripts in `scripts/`, not raw Python calls.

## Comments

Applies to every language in this repo: Python, PySpark, SQL, R, shell.

- One short comment line above a function, class, or SQL model, stating what it does. Nothing more.
- No comments inside a function body. If a line needs explaining, rename the variable or split the function instead of adding a comment.
- No docstrings longer than one line. No comment blocks. No restating the code in prose.
- Good: `# builds the gold fact_orders table`
- Bad: a comment above every line, a paragraph explaining the approach, a TODO essay.

## Python

- Format and lint with `ruff` before every commit.
- Type hint every function signature.
- Keep transforms as pure functions, input DataFrame in, output DataFrame out, so they stay unit testable.
- PySpark: prefer broadcast joins for small dimension tables, write partitioned Delta, never `.collect()` a large DataFrame to the driver.

## SQL

- Casts use `::VARCHAR` style, not `CAST(x AS VARCHAR)`, to satisfy SQLFluff.
- Run SQLFluff format before committing any `.sql` file.

## R

- One `library()` block at the top of the script or Rmd, nothing loaded mid file.
- Tidyverse style: snake_case names, pipe operator for multi step transforms.
- A script must run top to bottom with no manual steps in between.
- Write outputs (plots, tables) to a fixed output path, never overwrite source data.

## Shell

- Every script starts with `set -euo pipefail`.
- One script per pipeline stage, matching the layout in `scripts/`, don't fold two stages into one file.
- Log to that stage's own file under `logs/`, not only to stdout, this is what the ops monitoring reads.
- Read secrets from `.env` via `source`, never hardcode a credential or a connection string.

## Documentation

- No hyphens in prose anywhere in documentation, markdown files included. Use plain words instead.

## Git hygiene

- One branch per task, never commit straight to `main`. Name branches `feature/<short-name>`, `fix/<short-name>`, or `chore/<short-name>`.
- Commit messages: lower case, present tense, no trailing period. `fix silver dedupe on dim customers`, not `Fixed bug.`
- Small, single purpose commits, don't bundle an unrelated fix into a feature commit.
- Rebase onto `main` before opening a PR, keep history linear, no merge commits from stale branches.
- No local git hooks are installed. CI runs `pytest` and lint on every push, so verify locally before pushing.
- Open a PR to merge into `main`, reference the task in the PR description, not buried in a commit body. Squash merge, then delete the branch.
- No force push to `main` or to any branch someone else is also using.
- `.gitignore` covers `.venv`, `__pycache__`, `.Rproj.user`, `data/`, `logs/`, and `.env`, never commit these even by accident.
- Update `CHANGELOG.md` with every change that touches behavior, not every commit.

## Testing and data quality

- Every new Silver transform ships with a unit test before it is considered done.
- Never comment out or skip a failing test to get a green run, fix it or flag it in the PR description.
- A Great Expectations or dbt test failure blocks the pipeline, do not route around it.

## Boundaries

- Don't add a new dependency, Python or R, without checking `pyproject.toml` first, and don't add one at all if the standard library or an existing dependency already covers it.
- Don't invent config values, connection strings, or table names, ask if something is missing from `.env.example` or `ARCHITECTURE.md`.
- Prefer a targeted edit over rewriting a whole file for a small change.