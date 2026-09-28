-- ramadan versus non ramadan monthly revenue lift
WITH monthly AS (
    SELECT
        month::VARCHAR AS rev_month,
        max(is_ramadan::INT) = 1 AS is_ramadan,
        sum(revenue::NUMERIC) AS revenue
    FROM marts.ramadan_seasonality
    GROUP BY 1
),

split AS (
    SELECT
        avg(revenue) FILTER (WHERE is_ramadan) AS ramadan_avg,
        avg(revenue) FILTER (WHERE NOT is_ramadan) AS plain_avg
    FROM monthly
)

SELECT
    ramadan_avg,
    plain_avg,
    ramadan_avg / nullif(plain_avg, 0) - 1 AS lift_pct
FROM split;
