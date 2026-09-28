-- speeds ops page latest run lookups
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_task_started
ON ops.pipeline_runs (task_name, started_at DESC);

-- speeds quality trend lookups
CREATE INDEX IF NOT EXISTS idx_quality_results_suite_checked
ON ops.quality_results (suite_name, checked_at DESC);

-- speeds schema change feed lookups
CREATE INDEX IF NOT EXISTS idx_schema_changes_detected
ON ops.schema_changes (detected_at DESC);

-- speeds alert feed lookups
CREATE INDEX IF NOT EXISTS idx_alerts_detected
ON ops.alerts (detected_at DESC);
