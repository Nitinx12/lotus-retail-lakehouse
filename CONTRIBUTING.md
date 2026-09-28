# Contributing

`AGENTS.md` is the authority for how to work in this repo. This file
summarizes the workflow so a new contributor can open a correct pull
request on the first try.

## Setup

```bash
uv sync
cp .env.example .env
```

Fill `.env` with local values only. Never commit `.env`, `data/`, or
`logs/`. Staging and production secrets live in the secrets backend,
see `SECURITY.md`.

## Branches and commits

One branch per task, named `feature/<short-name>`, `fix/<short-name>`,
or `chore/<short-name>`. Never commit straight to `main`.

Keep commits small with one purpose each. Messages are lower case,
present tense, with no trailing period, for example
`fix silver dedupe on dim customers`.

Rebase onto `main` before opening a pull request so history stays
linear with no merge commits.

## Pull requests

Open a pull request to merge into `main`. The template asks for a task
reference plus the checks below. Maintainers squash merge, then delete
the branch.

## Checks

Run these before every commit, not just before a pull request:

```bash
make lint
uv run pytest tests/unit tests/smoke -q
```

The commit hook runs lint and format checks automatically and blocks
the commit on failure. A Great Expectations, dbt, or PL/pgSQL test
failure blocks the pipeline, never route around one, and never skip a
failing test to get a green run.

## Area notes

Python: format and lint with `ruff`, hint every function signature,
keep transforms pure so they stay unit testable. Every new Silver
transform ships with a unit test.

SQL: casts use `::VARCHAR` style, run SQLFluff format before committing
any `.sql` file.

R: one `library()` block at the top, tidyverse style with snake case
names and pipes, scripts run top to bottom, outputs go to the fixed
report path.

Shell: every script starts with `set -euo pipefail`, one script per
pipeline stage, logs go to that stage's own file under `logs/`.

Docs: prose uses plain words everywhere, markdown included.

## Changelog

Update `CHANGELOG.md` with every change that touches behavior.
