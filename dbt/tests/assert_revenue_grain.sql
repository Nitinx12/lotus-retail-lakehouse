-- one row per store and month
SELECT store_id, month, count(*) AS rows
FROM {{ ref('revenue_by_store_month') }}
GROUP BY 1, 2
HAVING count(*) > 1
