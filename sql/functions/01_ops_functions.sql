-- inserts one alert row returning its id
CREATE OR REPLACE FUNCTION ops.record_alert(
    p_source TEXT,
    p_severity TEXT,
    p_message TEXT
) RETURNS BIGINT
LANGUAGE plpgsql AS $$
DECLARE
    new_id BIGINT;
BEGIN
    INSERT INTO ops.alerts (source_task, severity, message)
    VALUES (p_source, p_severity, p_message)
    RETURNING alert_id INTO new_id;
    RETURN new_id;
END
$$;

-- stamps updated_at on every update
CREATE OR REPLACE FUNCTION ops.touch_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END
$$;

-- files an alert whenever a run row turns failed
CREATE OR REPLACE FUNCTION ops.alert_on_failed_run()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status = 'failed' THEN
        PERFORM ops.record_alert(
            NEW.task_name,
            'critical',
            'run failed for task ' || NEW.task_name::VARCHAR
                || coalesce(': ' || NEW.error_message::VARCHAR, '')
        );
    END IF;
    RETURN NEW;
END
$$;

-- files an alert when a suite drops below the pass threshold
CREATE OR REPLACE FUNCTION ops.alert_on_quality_drop()
RETURNS TRIGGER
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.success_percent::NUMERIC < 95.0 THEN
        PERFORM ops.record_alert(
            NEW.suite_name,
            'warning',
            'suite ' || NEW.suite_name::VARCHAR
                || ' dropped to ' || NEW.success_percent::VARCHAR || ' percent'
        );
    END IF;
    RETURN NEW;
END
$$;
