CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.fact_orders (
    order_id VARCHAR PRIMARY KEY,
    order_date DATE,
    customer_id VARCHAR,
    customer_sk BIGINT
);

CREATE TABLE IF NOT EXISTS gold.fact_returns (
    return_id VARCHAR PRIMARY KEY,
    order_id VARCHAR,
    return_amount NUMERIC
);

CREATE TABLE IF NOT EXISTS gold.fact_order_details (
    order_id VARCHAR,
    product_id VARCHAR
);

DELETE FROM gold.fact_order_details;
DELETE FROM gold.fact_returns;
DELETE FROM gold.fact_orders;

INSERT INTO gold.fact_orders VALUES
    ('o1', CURRENT_DATE - 1, 'a', 1),
    ('o2', CURRENT_DATE - 2, 'b', 2);

INSERT INTO gold.fact_returns VALUES
    ('r1', 'o1', 10.0);

INSERT INTO gold.fact_order_details VALUES
    ('o1', 'p1'),
    ('o2', 'p2');
