-- monthly revenue with growth and margin off the revenue mart
WITH monthly AS (
    SELECT
        month::VARCHAR AS rev_month,
        sum(revenue::NUMERIC) AS revenue,
        sum(cost::NUMERIC) AS total_cost,
        sum(orders::INT) AS orders
    FROM marts.revenue_by_store_month
    GROUP BY rev_month
)

SELECT
    rev_month,
    revenue,
    (revenue - total_cost) / nullif(revenue, 0) AS margin,
    revenue / nullif(lag(revenue) OVER (ORDER BY rev_month), 0)
    - 1 AS mom_growth,
    revenue / nullif(lag(revenue, 12) OVER (ORDER BY rev_month), 0)
    - 1 AS yoy_growth
FROM monthly
ORDER BY rev_month;
