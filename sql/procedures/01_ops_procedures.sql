-- marks running tasks older than the cutoff as failed
CREATE OR REPLACE PROCEDURE ops.close_stuck_runs(
    p_max_age INTERVAL DEFAULT INTERVAL '2 hours'
)
LANGUAGE plpgsql AS $$
DECLARE
    rec RECORD;
    closed INT := 0;
BEGIN
    FOR rec IN
        SELECT run_id, task_name
        FROM ops.pipeline_runs
        WHERE status = 'running'
        AND started_at < now() - p_max_age
    LOOP
        UPDATE ops.pipeline_runs
        SET status = 'failed',
            ended_at = now(),
            error_message = 'closed as stuck by ops.close_stuck_runs'
        WHERE run_id = rec.run_id
        AND task_name = rec.task_name;
        closed := closed + 1;
    END LOOP;
    RAISE NOTICE 'close_stuck_runs closed % stuck tasks', closed;
END
$$;

-- deletes old successful history keeping failures longer
CREATE OR REPLACE PROCEDURE ops.purge_old_runs(
    p_retention_days INT DEFAULT 90
)
LANGUAGE plpgsql AS $$
DECLARE
    removed_runs INT;
    removed_quality INT;
BEGIN
    DELETE FROM ops.pipeline_runs
    WHERE status = 'success'
    AND started_at < now() - make_interval(days => p_retention_days);
    GET DIAGNOSTICS removed_runs = ROW_COUNT;
    DELETE FROM ops.quality_results
    WHERE checked_at < now() - make_interval(days => p_retention_days);
    GET DIAGNOSTICS removed_quality = ROW_COUNT;
    RAISE NOTICE 'purge_old_runs removed % runs and % quality rows', removed_runs, removed_quality;
END
$$;
