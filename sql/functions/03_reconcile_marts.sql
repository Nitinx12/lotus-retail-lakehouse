-- reconciles each mart against its base table looping over checks
CREATE OR REPLACE FUNCTION gold.reconcile_marts()
RETURNS TABLE (check_name TEXT, success_percent NUMERIC, failed INT)
LANGUAGE plpgsql AS $$
DECLARE
    rec RECORD;
    mart_val NUMERIC;
    base_val NUMERIC;
    pct NUMERIC;
    bad INT;
BEGIN
    FOR rec IN
        SELECT * FROM (VALUES
            (
                'revenue_totals',
                'SELECT coalesce(sum(revenue::NUMERIC), 0) FROM marts.revenue_by_store_month',
                'SELECT coalesce(sum(total_revenue::NUMERIC), 0) FROM gold.fact_orders'
            ),
            (
                'ramadan_totals',
                'SELECT coalesce(sum(revenue::NUMERIC), 0) FROM marts.ramadan_seasonality',
                'SELECT coalesce(sum(total_revenue::NUMERIC), 0) FROM gold.fact_orders'
            ),
            (
                'rate_products',
                'SELECT count(*)::NUMERIC FROM marts.return_rate_by_product',
                'SELECT count(DISTINCT product_id::VARCHAR)::NUMERIC FROM gold.fact_order_details'
            )
        ) AS checks(check_name, mart_sql, base_sql)
    LOOP
        EXECUTE rec.mart_sql INTO mart_val;
        EXECUTE rec.base_sql INTO base_val;
        IF mart_val = 0 AND base_val = 0 THEN
            pct := 100.0;
            bad := 0;
        ELSIF base_val = 0 THEN
            pct := 0.0;
            bad := 1;
        ELSE
            pct := 100.0 * least(mart_val, base_val) / greatest(mart_val, base_val);
            bad := CASE WHEN mart_val = base_val THEN 0 ELSE 1 END;
        END IF;
        check_name := rec.check_name;
        success_percent := round(pct, 2);
        failed := bad;
        RETURN NEXT;
    END LOOP;
END
$$;
