INSERT INTO gold.fact_orders
(
    order_id,
    order_date,
    date_id,
    customer_id,
    store_id,
    total_revenue,
    total_cost,
    customer_sk
)
VALUES
('o3', CURRENT_DATE + 1, 20220101, 'c', 1, 5.0, 2.0, NULL);

INSERT INTO gold.fact_returns (return_id, order_id, return_amount) VALUES
('r2', 'o3', -5.0),
('r3', 'ghost', 7.0);
