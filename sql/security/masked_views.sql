-- exposes masked customer pii to general bi roles
CREATE SCHEMA IF NOT EXISTS gold;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'gold' AND table_name = 'dim_customers'
    ) THEN
        EXECUTE '
            CREATE OR REPLACE VIEW gold.dim_customers_masked AS
            SELECT
                customer_id::VARCHAR AS customer_id,
                regexp_replace(full_name::VARCHAR, ''([A-Za-z])[A-Za-z]*'', ''\1'', ''g'') AS name_initials,
                encode(sha256(email::VARCHAR::bytea), ''hex'') AS email_hash,
                city::VARCHAR AS city,
                region::VARCHAR AS region,
                loyalty_tier::VARCHAR AS loyalty_tier
            FROM gold.dim_customers';
    END IF;
END
$$;
