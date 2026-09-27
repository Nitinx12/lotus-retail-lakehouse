-- blocks ingestion when a previous run never finished
DO $$
DECLARE
    stuck INT;
BEGIN
    SELECT count(*) INTO stuck
    FROM ops.pipeline_runs
    WHERE status = 'running'
    AND task_name <> 'plpgsql_source';
    IF stuck > 0 THEN
        RAISE EXCEPTION 'plpgsql source check failed: % stuck running tasks', stuck;
    END IF;
END
$$;
