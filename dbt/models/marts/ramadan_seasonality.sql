-- monthly revenue inside versus outside ramadan
SELECT
    to_char(o.order_date::DATE, 'YYYY-MM') AS month,
    d.is_ramadan AS is_ramadan,
    sum(o.total_revenue::NUMERIC) AS revenue,
    count(DISTINCT o.order_id::VARCHAR) AS orders
FROM {{ source('gold', 'fact_orders') }} AS o
LEFT JOIN {{ source('gold', 'dim_date') }} AS d
    ON d.date_id = o.date_id
GROUP BY 1, 2
