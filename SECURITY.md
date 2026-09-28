# Security Policy

## Supported versions

Only the `main` branch is supported with security fixes. Work on
feature branches should rebase onto `main` promptly.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Report it
through a private security advisory:

https://github.com/Nitinx12/lotus-retail-lakehouse/security/advisories/new

Include what is affected, how to reproduce, and what you think the
impact is. Expect an initial response within a few days. Do not
disclose the issue publicly until a fix is merged.

## Secrets

`.env` files hold local development values only and must never be
committed. The commit hook blocks any staged `.env` file.
Staging and production credentials live in the secrets backend and
reach Airflow as connections, Databricks jobs as secret scopes, and
local Docker runs as environment variables. Connection strings and
passwords must never appear in source, logs, or issue text.

## Customer data

`dim_customers` carries names plus contact fields. General pages and
roles only read the masked view `gold.dim_customers_masked`. The
unmasked table is limited to the `pii_reader` role on the ops path.
Enforced with Postgres grants, not convention. See `ARCHITECTURE.md`
Section 10.

## Access control

Service accounts follow least privilege: Bronze writers cannot touch
Gold, and the dashboard connects through the pooler with a BI scoped
role. The dashboard itself has no login yet, so run it behind a
network boundary or reverse proxy until auth lands.

## Dependencies

Dependabot opens weekly pull requests for Python, GitHub Actions, and
Docker updates. Treat a security flagged update as urgent and merge it
ahead of feature work.
