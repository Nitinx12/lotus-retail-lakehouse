DO $$
DECLARE
  r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'ops' LOOP
    EXECUTE format('ALTER TABLE ops.%I OWNER TO lotus_pipeline', r.tablename);
  END LOOP;
END
$$;

GRANT SELECT ON ALL TABLES IN SCHEMA ops TO lotus_app;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO lotus_app;
GRANT SELECT ON ALL TABLES IN SCHEMA marts TO lotus_app;
GRANT SELECT ON ALL TABLES IN SCHEMA gold TO lotus_api_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA marts TO lotus_api_reader;
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_tables
        WHERE schemaname = 'gold' AND tablename = 'dim_customers'
    ) THEN
        REVOKE ALL ON gold.dim_customers FROM lotus_app;
        REVOKE ALL ON gold.dim_customers FROM lotus_api_reader;
    END IF;
END
$$;
GRANT USAGE ON SCHEMA ops TO lotus_api_reader;
GRANT SELECT ON ops.pipeline_runs TO lotus_api_reader;

ALTER DEFAULT PRIVILEGES FOR ROLE lotus_pipeline IN SCHEMA marts
GRANT SELECT ON TABLES TO lotus_app;
ALTER DEFAULT PRIVILEGES FOR ROLE lotus_pipeline IN SCHEMA gold
GRANT SELECT ON TABLES TO lotus_app;
ALTER DEFAULT PRIVILEGES FOR ROLE lotus_pipeline IN SCHEMA gold
GRANT SELECT ON TABLES TO lotus_api_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE lotus_pipeline IN SCHEMA marts
GRANT SELECT ON TABLES TO lotus_app;
ALTER DEFAULT PRIVILEGES FOR ROLE lotus_pipeline IN SCHEMA marts
GRANT SELECT ON TABLES TO lotus_api_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE lotus_pipeline IN SCHEMA ops
GRANT SELECT ON TABLES TO lotus_app;
