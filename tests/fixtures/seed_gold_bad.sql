INSERT INTO gold.fact_orders VALUES
    ('o3', CURRENT_DATE + 1, 'c', NULL);

INSERT INTO gold.fact_returns VALUES
    ('r2', 'o3', -5.0),
    ('r3', 'ghost', 7.0);
