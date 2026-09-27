-- restricts unmasked pii and opens the masked view
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'gold' AND table_name = 'dim_customers'
    ) THEN
        EXECUTE 'REVOKE ALL ON gold.dim_customers FROM PUBLIC';
        EXECUTE 'GRANT SELECT ON gold.dim_customers TO lotus_pii_reader';
        EXECUTE 'GRANT SELECT ON gold.dim_customers_masked TO lotus_bi';
        EXECUTE 'GRANT SELECT ON gold.dim_customers_masked TO lotus_app';
    END IF;
END
$$;
