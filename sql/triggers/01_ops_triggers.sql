-- keeps checkpoint write stamps current
DROP TRIGGER IF EXISTS trg_touch_checkpoints ON ops.extract_checkpoints;
CREATE TRIGGER trg_touch_checkpoints
BEFORE UPDATE ON ops.extract_checkpoints
FOR EACH ROW EXECUTE FUNCTION ops.touch_updated_at();

-- fires alerts on failed run rows
DROP TRIGGER IF EXISTS trg_alert_failed_run ON ops.pipeline_runs;
CREATE TRIGGER trg_alert_failed_run
AFTER INSERT OR UPDATE ON ops.pipeline_runs
FOR EACH ROW EXECUTE FUNCTION ops.alert_on_failed_run();

-- fires alerts on low suite scores
DROP TRIGGER IF EXISTS trg_alert_quality_drop ON ops.quality_results;
CREATE TRIGGER trg_alert_quality_drop
AFTER INSERT ON ops.quality_results
FOR EACH ROW EXECUTE FUNCTION ops.alert_on_quality_drop();
