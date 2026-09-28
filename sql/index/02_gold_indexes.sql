-- creates gold serving indexes only where the table exists
DO $$
DECLARE
    defs TEXT[][] := ARRAY[
        ['idx_fact_orders_order_date', 'gold', 'fact_orders', '(order_date)', ''],
        ['idx_fact_orders_store_month', 'gold', 'fact_orders', '(store_id, order_date)', ''],
        ['idx_fact_order_details_order_id', 'gold', 'fact_order_details', '(order_id)', ''],
        ['idx_fact_order_details_product_id', 'gold', 'fact_order_details', '(product_id)', ''],
        ['idx_fact_returns_order_id', 'gold', 'fact_returns', '(order_id)', ''],
        ['idx_dim_customers_customer_id', 'gold', 'dim_customers', '(customer_id)', ''],
        ['idx_dim_customers_current', 'gold', 'dim_customers', '(is_current)', 'WHERE is_current'],
        ['idx_marts_revenue_month', 'marts', 'revenue_by_store_month', '(month)', ''],
        ['idx_marts_ramadan_month', 'marts', 'ramadan_seasonality', '(month)', '']
    ];
    d TEXT[];
BEGIN
    FOREACH d SLICE 1 IN ARRAY defs
    LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = d[2] AND table_name = d[3]
        ) THEN
            EXECUTE format(
                'CREATE INDEX IF NOT EXISTS %I ON %I.%I %s %s',
                d[1], d[2], d[3], d[4], d[5]
            );
        END IF;
    END LOOP;
END
$$;
