## What

Describe the change in one paragraph. Keep the commit history small with
one purpose per commit.

## Task reference

Link the task or issue this PR resolves, for example `Closes #123`.
The task reference lives here in the PR description, not in a commit body.

## Checks

- [ ] `make lint` passes locally
- [ ] `pytest` passes locally (`tests/unit` plus `tests/smoke` at minimum)
- [ ] Branch is up to date with `main` with linear history and no merge commits
- [ ] `CHANGELOG.md` updated for every behavior change
- [ ] No `.env`, `data/`, `logs/`, or credential files included
- [ ] Docs prose uses plain words throughout
