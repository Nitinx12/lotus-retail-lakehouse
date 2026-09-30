# databricks silver job cleaning bronze into silver per architecture section 6
from __future__ import annotations

from src.silver.scd2 import (
    CUSTOMER_TRACKED,
    EMPLOYEE_TRACKED,
    apply_scd2,
)
from src.silver.transforms import (
    clean_customers,
    clean_orders,
    clean_products,
    drop_extract_meta,
    enrich_returns,
    union_orders,
)
from src.spark.session import catalog_for, get_spark, resolve_env


# cleans every table and versions the two type 2 dimensions
def main() -> None:
    catalog = catalog_for(resolve_env())
    spark = get_spark("lotus-silver")

    def bronze(table: str):
        return spark.read.table(f"{catalog}.bronze.{table}")

    def write(frame, table: str) -> None:
        frame.write.format("delta").mode("overwrite").saveAsTable(
            f"{catalog}.silver.{table}"
        )

    write(clean_customers(bronze("dim_customers")), "dim_customers")
    write(clean_products(bronze("dim_products")), "dim_products")
    for table in ("dim_stores", "dim_employees", "dim_date", "fact_order_details"):
        write(drop_extract_meta(bronze(table)), table)
    orders = union_orders(
        clean_orders(bronze("fact_orders_2022_2023")),
        clean_orders(bronze("fact_orders_2024")),
    )
    write(orders, "fact_orders")
    write(
        enrich_returns(
            drop_extract_meta(bronze("fact_returns")),
            drop_extract_meta(bronze("fact_order_details")),
        ),
        "fact_returns",
    )
    bounds = orders.agg({"order_date": "max"}).collect()[0][0]
    business_date = str(bounds)
    customers = spark.read.table(f"{catalog}.silver.dim_customers")
    apply_scd2(
        None, customers, "customer_id", CUSTOMER_TRACKED, "customer_sk", business_date
    ).write.format("delta").mode("overwrite").saveAsTable(
        f"{catalog}.silver.dim_customers_scd2"
    )
    employees = spark.read.table(f"{catalog}.silver.dim_employees")
    apply_scd2(
        None, employees, "employee_id", EMPLOYEE_TRACKED, "employee_sk", business_date
    ).write.format("delta").mode("overwrite").saveAsTable(
        f"{catalog}.silver.dim_employees_scd2"
    )


if __name__ == "__main__":
    main()
