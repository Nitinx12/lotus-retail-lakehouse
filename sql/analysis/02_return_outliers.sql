-- product return outliers by portfolio z score
WITH stats AS (
    SELECT
        avg(return_rate::NUMERIC) AS mu,
        stddev_pop(return_rate::NUMERIC) AS sd
    FROM marts.return_rate_by_product
)

SELECT
    r.product_id::VARCHAR AS product_id,
    r.times_ordered::INT AS times_ordered,
    r.times_returned::INT AS times_returned,
    r.return_rate::NUMERIC AS return_rate,
    (r.return_rate::NUMERIC - s.mu) / nullif(s.sd, 0) AS z_score
FROM marts.return_rate_by_product AS r, stats AS s
ORDER BY r.return_rate DESC;
