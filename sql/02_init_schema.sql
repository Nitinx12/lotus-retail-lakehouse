-- ============================================================
-- OLA PROJECT
-- PostgreSQL Schema Initialization
-- ============================================================

BEGIN;

-- =============================================================
-- CREATE SCHEMAS
-- =============================================================

CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- =============================================================
-- Set default search path
-- =============================================================

SET search_path TO bronze, silver, gold, public;

-- =============================================================
-- Verification
-- =============================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.schemata
        WHERE schema_name = 'bronze'
    ) THEN
        RAISE EXCEPTION 'Schema bronze was not created';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.schemata
        WHERE schema_name = 'silver'
    ) THEN
        RAISE EXCEPTION 'Schema silver was not created';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.schemata
        WHERE schema_name = 'gold'
    ) THEN
        RAISE EXCEPTION 'Schema gold was not created';
    END IF;

    RAISE NOTICE 'Ola schemas initialized successfully';
END $$;


COMMIT;

-- =============================================================
-- psql -U postgres -d ola -f .\sql\02_init_schema.sql
-- =============================================================