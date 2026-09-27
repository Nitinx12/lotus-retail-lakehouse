CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.dim_date (
    date_id BIGINT,
    is_ramadan INT
);

CREATE TABLE IF NOT EXISTS gold.dim_stores (
    store_id BIGINT
);

CREATE TABLE IF NOT EXISTS gold.dim_products (
    product_id VARCHAR
);

CREATE TABLE IF NOT EXISTS gold.fact_orders (
    order_id VARCHAR PRIMARY KEY,
    order_date DATE,
    date_id BIGINT,
    customer_id VARCHAR,
    store_id BIGINT,
    total_revenue NUMERIC,
    total_cost NUMERIC,
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
DELETE FROM gold.dim_date;
DELETE FROM gold.dim_stores;
DELETE FROM gold.dim_products;

INSERT INTO gold.dim_date (date_id, is_ramadan) VALUES
(20220101, 0),
(20220102, 0);

INSERT INTO gold.dim_stores (store_id) VALUES
(1);

INSERT INTO gold.dim_products (product_id) VALUES
('p1'),
('p2');

INSERT INTO gold.fact_orders
(
    order_id,
    order_date,
    date_id,
    customer_id,
    store_id,
    total_revenue,
    total_cost,
    customer_sk
)
VALUES
('o1', CURRENT_DATE - 1, 20220101, 'a', 1, 10.0, 4.0, 1),
('o2', CURRENT_DATE - 2, 20220102, 'b', 1, 20.0, 8.0, 2);

INSERT INTO gold.fact_returns (return_id, order_id, return_amount) VALUES
('r1', 'o1', 10.0);

INSERT INTO gold.fact_order_details (order_id, product_id) VALUES
('o1', 'p1'),
('o2', 'p2');
