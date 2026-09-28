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

ALTER DEFAULT PRIVILEGES FOR ROLE lotus_pipeline IN SCHEMA marts
GRANT SELECT ON TABLES TO lotus_app;
ALTER DEFAULT PRIVILEGES FOR ROLE lotus_pipeline IN SCHEMA ops
GRANT SELECT ON TABLES TO lotus_app;
