-- return rate per product from details and returned order ids
WITH returned AS (
    SELECT DISTINCT order_id::VARCHAR AS order_id
    FROM {{ source('gold', 'fact_returns') }}
)
SELECT
    d.product_id::VARCHAR AS product_id,
    count(*) AS times_ordered,
    sum(CASE WHEN r.order_id IS NULL THEN 0 ELSE 1 END) AS times_returned,
    sum(CASE WHEN r.order_id IS NULL THEN 0 ELSE 1 END)::NUMERIC
        / NULLIF(count(*), 0) AS return_rate
FROM {{ source('gold', 'fact_order_details') }} AS d
LEFT JOIN returned AS r
    ON r.order_id = d.order_id::VARCHAR
GROUP BY 1
