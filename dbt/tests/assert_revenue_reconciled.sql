-- mart revenue reconciles to gold facts
SELECT m.revenue AS mart_revenue, f.revenue AS fact_revenue
FROM (
    SELECT round(sum(revenue)::NUMERIC, 2) AS revenue
    FROM {{ ref('revenue_by_store_month') }}
) AS m
CROSS JOIN (
    SELECT round(sum(total_revenue::NUMERIC), 2) AS revenue
    FROM {{ source('gold', 'fact_orders') }}
) AS f
WHERE m.revenue <> f.revenue
