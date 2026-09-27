-- blocks promotion when gold holds impossible values
DO $$
DECLARE
    future_orders INT;
    negative_returns INT;
    orphan_returns INT;
    null_customer_sk INT;
BEGIN
    SELECT count(*) INTO future_orders
    FROM gold.fact_orders
    WHERE order_date::DATE > CURRENT_DATE;

    SELECT count(*) INTO negative_returns
    FROM gold.fact_returns
    WHERE return_amount::NUMERIC < 0;

    SELECT count(*) INTO orphan_returns
    FROM gold.fact_returns AS r
    WHERE NOT EXISTS (
        SELECT 1 FROM gold.fact_order_details AS d
        WHERE d.order_id::VARCHAR = r.order_id::VARCHAR
    );

    SELECT count(*) INTO null_customer_sk
    FROM gold.fact_orders
    WHERE customer_sk IS NULL;

    IF future_orders + negative_returns + orphan_returns + null_customer_sk > 0 THEN
        RAISE EXCEPTION
            'plpgsql gold check failed: future_orders=% negative_returns=% orphan_returns=% null_customer_sk=%',
            future_orders, negative_returns, orphan_returns, null_customer_sk;
    END IF;
END
$$;
