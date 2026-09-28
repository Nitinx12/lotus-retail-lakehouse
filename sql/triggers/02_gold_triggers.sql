-- guards fact writes only where the serving tables exist
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'gold' AND table_name = 'fact_orders'
    ) THEN
        DROP TRIGGER IF EXISTS trg_guard_fact_order ON gold.fact_orders;
        CREATE TRIGGER trg_guard_fact_order
        BEFORE INSERT OR UPDATE ON gold.fact_orders
        FOR EACH ROW EXECUTE FUNCTION gold.guard_fact_order();
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'gold' AND table_name = 'fact_returns'
    ) THEN
        DROP TRIGGER IF EXISTS trg_guard_fact_return ON gold.fact_returns;
        CREATE TRIGGER trg_guard_fact_return
        BEFORE INSERT OR UPDATE ON gold.fact_returns
        FOR EACH ROW EXECUTE FUNCTION gold.guard_fact_return();
    END IF;
END
$$;
