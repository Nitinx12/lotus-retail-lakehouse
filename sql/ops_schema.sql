-- creates the ops monitoring schema
CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.pipeline_runs (
    run_id UUID NOT NULL,
    task_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    rows_in BIGINT,
    rows_out BIGINT,
    error_message TEXT,
    PRIMARY KEY (run_id, task_name)
);

CREATE TABLE IF NOT EXISTS ops.quality_results (
    run_id UUID NOT NULL,
    suite_name TEXT NOT NULL,
    success_percent NUMERIC,
    failed_expectations INT NOT NULL DEFAULT 0,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, suite_name)
);

CREATE TABLE IF NOT EXISTS ops.extract_checkpoints (
    source_collection TEXT PRIMARY KEY,
    last_object_id TEXT,
    last_loaded_at TIMESTAMPTZ,
    rows_copied BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ops.schema_changes (
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    table_name TEXT NOT NULL,
    column_name TEXT,
    change_type TEXT NOT NULL
);

-- records fired alerts for failures and quality drops
CREATE TABLE IF NOT EXISTS ops.alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_task TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'warning',
    message TEXT NOT NULL
);
