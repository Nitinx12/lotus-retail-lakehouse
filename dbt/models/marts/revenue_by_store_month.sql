-- monthly revenue and cost per store
SELECT
    store_id,
    to_char(order_date::DATE, 'YYYY-MM') AS month,
    sum(total_revenue::NUMERIC) AS revenue,
    sum(total_cost::NUMERIC) AS cost,
    count(DISTINCT order_id::VARCHAR) AS orders
FROM {{ source('gold', 'fact_orders') }}
GROUP BY 1, 2
