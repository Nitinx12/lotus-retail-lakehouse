using System;
using System.Collections.Generic;
using LotusApi.Models;
using Microsoft.EntityFrameworkCore;

namespace LotusApi.Data;

public partial class LotusGoldContext : DbContext
{
    public LotusGoldContext(DbContextOptions<LotusGoldContext> options)
        : base(options)
    {
    }

    public virtual DbSet<Alert> Alerts { get; set; }

    public virtual DbSet<DimCustomer> DimCustomers { get; set; }

    public virtual DbSet<DimCustomersMasked> DimCustomersMaskeds { get; set; }

    public virtual DbSet<DimDate> DimDates { get; set; }

    public virtual DbSet<DimEmployee> DimEmployees { get; set; }

    public virtual DbSet<DimProduct> DimProducts { get; set; }

    public virtual DbSet<DimStore> DimStores { get; set; }

    public virtual DbSet<ExtractCheckpoint> ExtractCheckpoints { get; set; }

    public virtual DbSet<FactOrder> FactOrders { get; set; }

    public virtual DbSet<FactOrderDetail> FactOrderDetails { get; set; }

    public virtual DbSet<FactReturn> FactReturns { get; set; }

    public virtual DbSet<PipelineRun> PipelineRuns { get; set; }

    public virtual DbSet<QualityResult> QualityResults { get; set; }

    public virtual DbSet<RamadanSeasonality> RamadanSeasonalities { get; set; }

    public virtual DbSet<ReturnRateByProduct> ReturnRateByProducts { get; set; }

    public virtual DbSet<RevenueByStoreMonth> RevenueByStoreMonths { get; set; }

    public virtual DbSet<SchemaChange> SchemaChanges { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Alert>(entity =>
        {
            entity.HasKey(e => e.AlertId).HasName("alerts_pkey");

            entity.ToTable("alerts", "ops");

            entity.HasIndex(e => e.DetectedAt, "idx_alerts_detected").IsDescending();

            entity.Property(e => e.AlertId).HasColumnName("alert_id");
            entity.Property(e => e.DetectedAt)
                .HasDefaultValueSql("now()")
                .HasColumnName("detected_at");
            entity.Property(e => e.Message).HasColumnName("message");
            entity.Property(e => e.Severity)
                .HasDefaultValueSql("'warning'::text")
                .HasColumnName("severity");
            entity.Property(e => e.SourceTask).HasColumnName("source_task");
        });

        modelBuilder.Entity<DimCustomer>(entity =>
        {
            entity
                .HasNoKey()
                .ToTable("dim_customers", "gold");

            entity.HasIndex(e => e.IsCurrent, "idx_dim_customers_current").HasFilter("is_current");

            entity.HasIndex(e => e.CustomerId, "idx_dim_customers_customer_id");

            entity.Property(e => e.AttributeHash).HasColumnName("attribute_hash");
            entity.Property(e => e.BatchId).HasColumnName("_batch_id");
            entity.Property(e => e.BirthDate).HasColumnName("birth_date");
            entity.Property(e => e.City).HasColumnName("city");
            entity.Property(e => e.CustomerId).HasColumnName("customer_id");
            entity.Property(e => e.CustomerSk).HasColumnName("customer_sk");
            entity.Property(e => e.EffectiveEndDate).HasColumnName("effective_end_date");
            entity.Property(e => e.EffectiveStartDate).HasColumnName("effective_start_date");
            entity.Property(e => e.Email).HasColumnName("email");
            entity.Property(e => e.FullName).HasColumnName("full_name");
            entity.Property(e => e.Gender).HasColumnName("gender");
            entity.Property(e => e.IsCurrent).HasColumnName("is_current");
            entity.Property(e => e.LoyaltyTier).HasColumnName("loyalty_tier");
            entity.Property(e => e.Phone).HasColumnName("phone");
            entity.Property(e => e.Region).HasColumnName("region");
            entity.Property(e => e.RegistrationDate).HasColumnName("registration_date");
        });

        modelBuilder.Entity<DimCustomersMasked>(entity =>
        {
            entity
                .HasNoKey()
                .ToView("dim_customers_masked", "gold");

            entity.Property(e => e.City)
                .HasColumnType("character varying")
                .HasColumnName("city");
            entity.Property(e => e.CustomerId)
                .HasColumnType("character varying")
                .HasColumnName("customer_id");
            entity.Property(e => e.EmailHash).HasColumnName("email_hash");
            entity.Property(e => e.LoyaltyTier)
                .HasColumnType("character varying")
                .HasColumnName("loyalty_tier");
            entity.Property(e => e.NameInitials).HasColumnName("name_initials");
            entity.Property(e => e.Region)
                .HasColumnType("character varying")
                .HasColumnName("region");
        });

        modelBuilder.Entity<DimDate>(entity =>
        {
            entity
                .HasNoKey()
                .ToTable("dim_date", "gold");

            entity.Property(e => e.BatchId).HasColumnName("_batch_id");
            entity.Property(e => e.DateId).HasColumnName("date_id");
            entity.Property(e => e.Day).HasColumnName("day");
            entity.Property(e => e.DayName).HasColumnName("day_name");
            entity.Property(e => e.DayOfWeek).HasColumnName("day_of_week");
            entity.Property(e => e.FullDate).HasColumnName("full_date");
            entity.Property(e => e.IsRamadan).HasColumnName("is_ramadan");
            entity.Property(e => e.IsWeekend).HasColumnName("is_weekend");
            entity.Property(e => e.Month).HasColumnName("month");
            entity.Property(e => e.MonthName).HasColumnName("month_name");
            entity.Property(e => e.Quarter).HasColumnName("quarter");
            entity.Property(e => e.QuarterName).HasColumnName("quarter_name");
            entity.Property(e => e.WeekOfYear).HasColumnName("week_of_year");
            entity.Property(e => e.Year).HasColumnName("year");
        });

        modelBuilder.Entity<DimEmployee>(entity =>
        {
            entity
                .HasNoKey()
                .ToTable("dim_employees", "gold");

            entity.Property(e => e.AttributeHash).HasColumnName("attribute_hash");
            entity.Property(e => e.BatchId).HasColumnName("_batch_id");
            entity.Property(e => e.EffectiveEndDate).HasColumnName("effective_end_date");
            entity.Property(e => e.EffectiveStartDate).HasColumnName("effective_start_date");
            entity.Property(e => e.EmployeeId).HasColumnName("employee_id");
            entity.Property(e => e.EmployeeSk).HasColumnName("employee_sk");
            entity.Property(e => e.FirstName).HasColumnName("first_name");
            entity.Property(e => e.Gender).HasColumnName("gender");
            entity.Property(e => e.HireDate).HasColumnName("hire_date");
            entity.Property(e => e.IsCurrent).HasColumnName("is_current");
            entity.Property(e => e.LastName).HasColumnName("last_name");
            entity.Property(e => e.MonthlySalaryEgp).HasColumnName("monthly_salary_egp");
            entity.Property(e => e.Role).HasColumnName("role");
            entity.Property(e => e.StoreId).HasColumnName("store_id");
        });

        modelBuilder.Entity<DimProduct>(entity =>
        {
            entity
                .HasNoKey()
                .ToTable("dim_products", "gold");

            entity.Property(e => e.BatchId).HasColumnName("_batch_id");
            entity.Property(e => e.Brand).HasColumnName("brand");
            entity.Property(e => e.Category).HasColumnName("category");
            entity.Property(e => e.Color).HasColumnName("color");
            entity.Property(e => e.IsActive).HasColumnName("is_active");
            entity.Property(e => e.ProductId).HasColumnName("product_id");
            entity.Property(e => e.ProductName).HasColumnName("product_name");
            entity.Property(e => e.Size).HasColumnName("size");
            entity.Property(e => e.StockQty).HasColumnName("stock_qty");
            entity.Property(e => e.Subcategory).HasColumnName("subcategory");
            entity.Property(e => e.UnitCost).HasColumnName("unit_cost");
            entity.Property(e => e.UnitPrice).HasColumnName("unit_price");
        });

        modelBuilder.Entity<DimStore>(entity =>
        {
            entity
                .HasNoKey()
                .ToTable("dim_stores", "gold");

            entity.Property(e => e.BatchId).HasColumnName("_batch_id");
            entity.Property(e => e.City).HasColumnName("city");
            entity.Property(e => e.District).HasColumnName("district");
            entity.Property(e => e.OpeningYear).HasColumnName("opening_year");
            entity.Property(e => e.Region).HasColumnName("region");
            entity.Property(e => e.SizeSqm).HasColumnName("size_sqm");
            entity.Property(e => e.StoreId).HasColumnName("store_id");
            entity.Property(e => e.StoreName).HasColumnName("store_name");
            entity.Property(e => e.StoreType).HasColumnName("store_type");
        });

        modelBuilder.Entity<ExtractCheckpoint>(entity =>
        {
            entity.HasKey(e => e.SourceCollection).HasName("extract_checkpoints_pkey");

            entity.ToTable("extract_checkpoints", "ops");

            entity.Property(e => e.SourceCollection).HasColumnName("source_collection");
            entity.Property(e => e.LastLoadedAt).HasColumnName("last_loaded_at");
            entity.Property(e => e.LastObjectId).HasColumnName("last_object_id");
            entity.Property(e => e.RowsCopied)
                .HasDefaultValue(0L)
                .HasColumnName("rows_copied");
            entity.Property(e => e.UpdatedAt)
                .HasDefaultValueSql("now()")
                .HasColumnName("updated_at");
        });

        modelBuilder.Entity<FactOrder>(entity =>
        {
            entity
                .HasNoKey()
                .ToTable("fact_orders", "gold");

            entity.HasIndex(e => e.OrderDate, "idx_fact_orders_order_date");

            entity.HasIndex(e => new { e.StoreId, e.OrderDate }, "idx_fact_orders_store_month");

            entity.Property(e => e.AttributeHash).HasColumnName("attribute_hash");
            entity.Property(e => e.BatchId).HasColumnName("_batch_id");
            entity.Property(e => e.BirthDate).HasColumnName("birth_date");
            entity.Property(e => e.City).HasColumnName("city");
            entity.Property(e => e.CustomerId).HasColumnName("customer_id");
            entity.Property(e => e.CustomerSk).HasColumnName("customer_sk");
            entity.Property(e => e.DateId).HasColumnName("date_id");
            entity.Property(e => e.EffectiveEndDate)
                .HasColumnType("timestamp without time zone")
                .HasColumnName("effective_end_date");
            entity.Property(e => e.EffectiveEndDateEmp)
                .HasColumnType("timestamp without time zone")
                .HasColumnName("effective_end_date_emp");
            entity.Property(e => e.EffectiveStartDate)
                .HasColumnType("timestamp without time zone")
                .HasColumnName("effective_start_date");
            entity.Property(e => e.EffectiveStartDateEmp)
                .HasColumnType("timestamp without time zone")
                .HasColumnName("effective_start_date_emp");
            entity.Property(e => e.Email).HasColumnName("email");
            entity.Property(e => e.EmployeeId).HasColumnName("employee_id");
            entity.Property(e => e.EmployeeSk).HasColumnName("employee_sk");
            entity.Property(e => e.FullName).HasColumnName("full_name");
            entity.Property(e => e.Gender).HasColumnName("gender");
            entity.Property(e => e.IsCurrent).HasColumnName("is_current");
            entity.Property(e => e.LoyaltyTier).HasColumnName("loyalty_tier");
            entity.Property(e => e.OrderDate).HasColumnName("order_date");
            entity.Property(e => e.OrderId).HasColumnName("order_id");
            entity.Property(e => e.OrderStatus).HasColumnName("order_status");
            entity.Property(e => e.PaymentMethod).HasColumnName("payment_method");
            entity.Property(e => e.Phone).HasColumnName("phone");
            entity.Property(e => e.Region).HasColumnName("region");
            entity.Property(e => e.RegistrationDate).HasColumnName("registration_date");
            entity.Property(e => e.StoreId).HasColumnName("store_id");
            entity.Property(e => e.TotalCost).HasColumnName("total_cost");
            entity.Property(e => e.TotalRevenue).HasColumnName("total_revenue");
        });

        modelBuilder.Entity<FactOrderDetail>(entity =>
        {
            entity
                .HasNoKey()
                .ToTable("fact_order_details", "gold");

            entity.HasIndex(e => e.OrderId, "idx_fact_order_details_order_id");

            entity.HasIndex(e => e.ProductId, "idx_fact_order_details_product_id");

            entity.Property(e => e.BatchId).HasColumnName("_batch_id");
            entity.Property(e => e.DetailId).HasColumnName("detail_id");
            entity.Property(e => e.DiscountPct).HasColumnName("discount_pct");
            entity.Property(e => e.LineTotalCost).HasColumnName("line_total_cost");
            entity.Property(e => e.LineTotalRevenue).HasColumnName("line_total_revenue");
            entity.Property(e => e.OrderId).HasColumnName("order_id");
            entity.Property(e => e.ProductId).HasColumnName("product_id");
            entity.Property(e => e.Quantity).HasColumnName("quantity");
            entity.Property(e => e.SellingPrice).HasColumnName("selling_price");
            entity.Property(e => e.UnitCost).HasColumnName("unit_cost");
            entity.Property(e => e.UnitPrice).HasColumnName("unit_price");
        });

        modelBuilder.Entity<FactReturn>(entity =>
        {
            entity
                .HasNoKey()
                .ToTable("fact_returns", "gold");

            entity.HasIndex(e => e.OrderId, "idx_fact_returns_order_id");

            entity.Property(e => e.BatchId).HasColumnName("_batch_id");
            entity.Property(e => e.CustomerSk).HasColumnName("customer_sk");
            entity.Property(e => e.EmployeeSk).HasColumnName("employee_sk");
            entity.Property(e => e.NItems).HasColumnName("n_items");
            entity.Property(e => e.OrderId).HasColumnName("order_id");
            entity.Property(e => e.OrderRevenue).HasColumnName("order_revenue");
            entity.Property(e => e.RefundMethod).HasColumnName("refund_method");
            entity.Property(e => e.ReturnAmount).HasColumnName("return_amount");
            entity.Property(e => e.ReturnDate).HasColumnName("return_date");
            entity.Property(e => e.ReturnId).HasColumnName("return_id");
            entity.Property(e => e.ReturnOrphan).HasColumnName("return_orphan");
            entity.Property(e => e.ReturnReason).HasColumnName("return_reason");
            entity.Property(e => e.ReturnStatus).HasColumnName("return_status");
            entity.Property(e => e.StoreId).HasColumnName("store_id");
        });

        modelBuilder.Entity<PipelineRun>(entity =>
        {
            entity.HasKey(e => new { e.RunId, e.TaskName }).HasName("pipeline_runs_pkey");

            entity.ToTable("pipeline_runs", "ops");

            entity.HasIndex(e => new { e.TaskName, e.StartedAt }, "idx_pipeline_runs_task_started").IsDescending(false, true);

            entity.Property(e => e.RunId).HasColumnName("run_id");
            entity.Property(e => e.TaskName).HasColumnName("task_name");
            entity.Property(e => e.EndedAt).HasColumnName("ended_at");
            entity.Property(e => e.ErrorMessage).HasColumnName("error_message");
            entity.Property(e => e.RowsIn).HasColumnName("rows_in");
            entity.Property(e => e.RowsOut).HasColumnName("rows_out");
            entity.Property(e => e.StartedAt)
                .HasDefaultValueSql("now()")
                .HasColumnName("started_at");
            entity.Property(e => e.Status).HasColumnName("status");
        });

        modelBuilder.Entity<QualityResult>(entity =>
        {
            entity.HasKey(e => new { e.RunId, e.SuiteName }).HasName("quality_results_pkey");

            entity.ToTable("quality_results", "ops");

            entity.HasIndex(e => new { e.SuiteName, e.CheckedAt }, "idx_quality_results_suite_checked").IsDescending(false, true);

            entity.Property(e => e.RunId).HasColumnName("run_id");
            entity.Property(e => e.SuiteName).HasColumnName("suite_name");
            entity.Property(e => e.CheckedAt)
                .HasDefaultValueSql("now()")
                .HasColumnName("checked_at");
            entity.Property(e => e.FailedExpectations)
                .HasDefaultValue(0)
                .HasColumnName("failed_expectations");
            entity.Property(e => e.SuccessPercent).HasColumnName("success_percent");
        });

        modelBuilder.Entity<RamadanSeasonality>(entity =>
        {
            entity
                .HasNoKey()
                .ToTable("ramadan_seasonality", "marts");

            entity.HasIndex(e => e.Month, "idx_marts_ramadan_month");

            entity.Property(e => e.IsRamadan).HasColumnName("is_ramadan");
            entity.Property(e => e.Month).HasColumnName("month");
            entity.Property(e => e.Orders).HasColumnName("orders");
            entity.Property(e => e.Revenue).HasColumnName("revenue");
        });

        modelBuilder.Entity<ReturnRateByProduct>(entity =>
        {
            entity
                .HasNoKey()
                .ToTable("return_rate_by_product", "marts");

            entity.Property(e => e.ProductId)
                .HasColumnType("character varying")
                .HasColumnName("product_id");
            entity.Property(e => e.ReturnRate).HasColumnName("return_rate");
            entity.Property(e => e.TimesOrdered).HasColumnName("times_ordered");
            entity.Property(e => e.TimesReturned).HasColumnName("times_returned");
        });

        modelBuilder.Entity<RevenueByStoreMonth>(entity =>
        {
            entity
                .HasNoKey()
                .ToTable("revenue_by_store_month", "marts");

            entity.HasIndex(e => e.Month, "idx_marts_revenue_month");

            entity.Property(e => e.Cost).HasColumnName("cost");
            entity.Property(e => e.Month).HasColumnName("month");
            entity.Property(e => e.Orders).HasColumnName("orders");
            entity.Property(e => e.Revenue).HasColumnName("revenue");
            entity.Property(e => e.StoreId).HasColumnName("store_id");
        });

        modelBuilder.Entity<SchemaChange>(entity =>
        {
            entity
                .HasNoKey()
                .ToTable("schema_changes", "ops");

            entity.HasIndex(e => e.DetectedAt, "idx_schema_changes_detected").IsDescending();

            entity.Property(e => e.ChangeType).HasColumnName("change_type");
            entity.Property(e => e.ColumnName).HasColumnName("column_name");
            entity.Property(e => e.DetectedAt)
                .HasDefaultValueSql("now()")
                .HasColumnName("detected_at");
            entity.Property(e => e.TableName).HasColumnName("table_name");
        });

        OnModelCreatingPartial(modelBuilder);
    }

    partial void OnModelCreatingPartial(ModelBuilder modelBuilder);
}
