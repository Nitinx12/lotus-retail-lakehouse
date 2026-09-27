-- creates least privilege roles for the serving warehouse
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lotus_app') THEN
        CREATE ROLE lotus_app WITH LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lotus_ops') THEN
        CREATE ROLE lotus_ops WITH LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lotus_pii_reader') THEN
        CREATE ROLE lotus_pii_reader WITH LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'lotus_bi') THEN
        CREATE ROLE lotus_bi WITH NOLOGIN;
    END IF;
END
$$;

-- lets the app role assume the general bi role
GRANT lotus_bi TO lotus_app;
