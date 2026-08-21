-- =====================================================================
-- Data quality test log table
-- One row per check per run, so you can compare runs over time and
-- query PASS/FAIL/INFO status directly instead of eyeballing 10
-- separate result sets.
-- =====================================================================
CREATE TABLE IF NOT EXISTS dq_test_log (
    log_id    SERIAL PRIMARY KEY,
    run_at    TIMESTAMP NOT NULL,
    test_no   INT NOT NULL,
    test_name TEXT NOT NULL,
    status    TEXT NOT NULL,      -- PASS / FAIL / INFO
    details   TEXT
);

-- =====================================================================
-- Procedure: run_data_quality_tests
-- Runs every check from data_quality_test.sql, in order, in a single
-- call, and writes one row per check into dq_test_log.
--
-- NOTE: Tests 1 and 5 originally referenced a table called "booking"
-- (singular). Your load scripts (09_pop_dims.sql, 10_pop_fact.sql)
-- both load from "bookings" (plural), so this procedure uses
-- "bookings" to match the real source table. Update below if that
-- assumption is wrong.
--
-- Usage:
--   CALL run_data_quality_tests();
--   SELECT * FROM dq_test_log ORDER BY run_at DESC, test_no;
-- =====================================================================
CREATE OR REPLACE PROCEDURE run_data_quality_tests()
LANGUAGE plpgsql
AS $$
DECLARE
    v_run_at          TIMESTAMP := clock_timestamp();
    v_source_count    INT;
    v_fact_count      INT;
    v_null_date       INT;
    v_null_vehicle    INT;
    v_null_payment    INT;
    v_null_status     INT;
    v_null_pickup     INT;
    v_null_drop       INT;
    v_dv_source       INT;
    v_dv_dim          INT;
    v_dp_source       INT;
    v_dp_dim          INT;
    v_dd_source       INT;
    v_dd_dim          INT;
    v_invalid_measure INT;
    v_invalid_rating  INT;
    v_min_date        DATE;
    v_max_date        DATE;
    v_distinct_days   INT;
    r                 RECORD;
BEGIN

    ---------------------------------------------------------------
    -- TEST 1: row count match between source and fact table
    ---------------------------------------------------------------
    SELECT COUNT(*) INTO v_source_count FROM bookings;
    SELECT COUNT(*) INTO v_fact_count FROM fact_bookings;
    INSERT INTO dq_test_log(run_at, test_no, test_name, status, details)
    VALUES (v_run_at, 1, 'Row count match',
            CASE WHEN v_source_count = v_fact_count THEN 'PASS' ELSE 'FAIL' END,
            format('source_count=%s fact_count=%s', v_source_count, v_fact_count));

    ---------------------------------------------------------------
    -- TEST 2: duplicate booking_id in fact table
    ---------------------------------------------------------------
    FOR r IN
        SELECT booking_id, COUNT(*) AS cnt
        FROM fact_bookings
        GROUP BY booking_id
        HAVING COUNT(*) > 1
    LOOP
        INSERT INTO dq_test_log(run_at, test_no, test_name, status, details)
        VALUES (v_run_at, 2, 'Duplicate booking_id', 'FAIL',
                format('booking_id=%s count=%s', r.booking_id, r.cnt));
    END LOOP;
    IF NOT FOUND THEN
        INSERT INTO dq_test_log(run_at, test_no, test_name, status, details)
        VALUES (v_run_at, 2, 'Duplicate booking_id', 'PASS', 'No duplicate booking_id values');
    END IF;

    ---------------------------------------------------------------
    -- TEST 3: null foreign key check across all dimension keys
    ---------------------------------------------------------------
    SELECT
        SUM(CASE WHEN date_key IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN vehicle_type_key IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN payment_method_key IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN booking_status_key IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN pickup_location_key IS NULL THEN 1 ELSE 0 END),
        SUM(CASE WHEN drop_location_key IS NULL THEN 1 ELSE 0 END)
    INTO v_null_date, v_null_vehicle, v_null_payment, v_null_status, v_null_pickup, v_null_drop
    FROM fact_bookings;

    INSERT INTO dq_test_log(run_at, test_no, test_name, status, details) VALUES
    (v_run_at, 3, 'Null FK: date_key',            CASE WHEN v_null_date    = 0 THEN 'PASS' ELSE 'FAIL' END, format('null_count=%s', v_null_date)),
    (v_run_at, 3, 'Null FK: vehicle_type_key',    CASE WHEN v_null_vehicle = 0 THEN 'PASS' ELSE 'FAIL' END, format('null_count=%s', v_null_vehicle)),
    (v_run_at, 3, 'Null FK: payment_method_key',  CASE WHEN v_null_payment = 0 THEN 'PASS' ELSE 'FAIL' END, format('null_count=%s', v_null_payment)),
    (v_run_at, 3, 'Null FK: booking_status_key',  CASE WHEN v_null_status  = 0 THEN 'PASS' ELSE 'FAIL' END, format('null_count=%s', v_null_status)),
    (v_run_at, 3, 'Null FK: pickup_location_key', CASE WHEN v_null_pickup  = 0 THEN 'PASS' ELSE 'FAIL' END, format('null_count=%s', v_null_pickup)),
    (v_run_at, 3, 'Null FK: drop_location_key',   CASE WHEN v_null_drop    = 0 THEN 'PASS' ELSE 'FAIL' END, format('null_count=%s', v_null_drop));

    ---------------------------------------------------------------
    -- TEST 4: orphaned foreign keys
    ---------------------------------------------------------------
    FOR r IN
        SELECT 'vehicle_type' AS dim, COUNT(*) AS orphaned
        FROM fact_bookings f
        LEFT JOIN dim_vehicle_type vt ON vt.vehicle_type_key = f.vehicle_type_key
        WHERE f.vehicle_type_key IS NOT NULL AND vt.vehicle_type_key IS NULL

        UNION ALL

        SELECT 'payment_method', COUNT(*)
        FROM fact_bookings f
        LEFT JOIN dim_payment_method pm ON pm.payment_method_key = f.payment_method_key
        WHERE f.payment_method_key IS NOT NULL AND pm.payment_method_key IS NULL

        UNION ALL

        SELECT 'date', COUNT(*)
        FROM fact_bookings f
        LEFT JOIN dim_date d ON d.date_key = f.date_key
        WHERE f.date_key IS NOT NULL AND d.date_key IS NULL
    LOOP
        INSERT INTO dq_test_log(run_at, test_no, test_name, status, details)
        VALUES (v_run_at, 4, format('Orphaned FK: %s', r.dim),
                CASE WHEN r.orphaned = 0 THEN 'PASS' ELSE 'FAIL' END,
                format('orphaned_count=%s', r.orphaned));
    END LOOP;

    ---------------------------------------------------------------
    -- TEST 5: distinct value count match (dimension completeness)
    ---------------------------------------------------------------
    SELECT
        (SELECT COUNT(DISTINCT "Vehicle_Type") FROM bookings),
        (SELECT COUNT(*) FROM dim_vehicle_type),
        (SELECT COUNT(DISTINCT COALESCE("Payment_Method", 'N/A - Trip Not Completed')) FROM bookings),
        (SELECT COUNT(*) FROM dim_payment_method),
        (SELECT COUNT(DISTINCT TO_CHAR("Date"::DATE, 'YYYYMMDD')) FROM bookings),
        (SELECT COUNT(*) FROM dim_date)
    INTO v_dv_source, v_dv_dim, v_dp_source, v_dp_dim, v_dd_source, v_dd_dim;

    INSERT INTO dq_test_log(run_at, test_no, test_name, status, details) VALUES
    (v_run_at, 5, 'Dimension completeness: vehicle_type',   CASE WHEN v_dv_source = v_dv_dim THEN 'PASS' ELSE 'FAIL' END, format('source=%s dim=%s', v_dv_source, v_dv_dim)),
    (v_run_at, 5, 'Dimension completeness: payment_method', CASE WHEN v_dp_source = v_dp_dim THEN 'PASS' ELSE 'FAIL' END, format('source=%s dim=%s', v_dp_source, v_dp_dim)),
    (v_run_at, 5, 'Dimension completeness: date',           CASE WHEN v_dd_source = v_dd_dim THEN 'PASS' ELSE 'FAIL' END, format('source=%s dim=%s', v_dd_source, v_dd_dim));

    ---------------------------------------------------------------
    -- TEST 6: measure sanity check (no impossible negative values)
    ---------------------------------------------------------------
    SELECT COUNT(*) INTO v_invalid_measure
    FROM fact_bookings
    WHERE booking_value < 0
       OR ride_distance < 0
       OR v_tat < 0
       OR c_tat < 0;

    INSERT INTO dq_test_log(run_at, test_no, test_name, status, details)
    VALUES (v_run_at, 6, 'Measure sanity check (no negatives)',
            CASE WHEN v_invalid_measure = 0 THEN 'PASS' ELSE 'FAIL' END,
            format('invalid_row_count=%s', v_invalid_measure));

    ---------------------------------------------------------------
    -- TEST 7: rating range check
    ---------------------------------------------------------------
    SELECT COUNT(*) INTO v_invalid_rating
    FROM fact_bookings
    WHERE (customer_rating IS NOT NULL AND (customer_rating < 1 OR customer_rating > 5))
       OR (driver_ratings IS NOT NULL AND (driver_ratings < 1 OR driver_ratings > 5));

    INSERT INTO dq_test_log(run_at, test_no, test_name, status, details)
    VALUES (v_run_at, 7, 'Rating range check',
            CASE WHEN v_invalid_rating = 0 THEN 'PASS' ELSE 'FAIL' END,
            format('invalid_row_count=%s', v_invalid_rating));

    ---------------------------------------------------------------
    -- TEST 8: booking status logic consistency
    -- Automated check: a "Completed" booking should carry no cancel
    -- or incomplete flags. Every other status is logged as INFO for
    -- manual review, since the valid flag combinations for other
    -- statuses depend on business rules this script doesn't know.
    ---------------------------------------------------------------
    FOR r IN
        SELECT bs.booking_status,
            SUM(CASE WHEN f.canceled_by_customer_flag THEN 1 ELSE 0 END) AS flagged_canceled_by_customer,
            SUM(CASE WHEN f.canceled_by_driver_flag THEN 1 ELSE 0 END) AS flagged_canceled_by_driver,
            SUM(CASE WHEN f.incomplete_rides_flag THEN 1 ELSE 0 END) AS flagged_incomplete
        FROM fact_bookings f
        JOIN dim_booking_status bs ON bs.booking_status_key = f.booking_status_key
        GROUP BY bs.booking_status
        ORDER BY bs.booking_status
    LOOP
        INSERT INTO dq_test_log(run_at, test_no, test_name, status, details)
        VALUES (
            v_run_at, 8, format('Status logic: %s', r.booking_status),
            CASE
                WHEN r.booking_status ILIKE 'Completed'
                     AND (r.flagged_canceled_by_customer > 0
                          OR r.flagged_canceled_by_driver > 0
                          OR r.flagged_incomplete > 0)
                THEN 'FAIL'
                ELSE 'INFO'
            END,
            format('canceled_by_customer=%s canceled_by_driver=%s incomplete=%s',
                   r.flagged_canceled_by_customer, r.flagged_canceled_by_driver, r.flagged_incomplete)
        );
    END LOOP;

    ---------------------------------------------------------------
    -- TEST 9: date range sanity check (informational — no fixed
    -- expected range is known ahead of time, so this always logs
    -- as INFO for you to eyeball against your expected data window)
    ---------------------------------------------------------------
    SELECT MIN(d.full_date), MAX(d.full_date), COUNT(DISTINCT d.full_date)
    INTO v_min_date, v_max_date, v_distinct_days
    FROM fact_bookings f
    JOIN dim_date d ON d.date_key = f.date_key;

    INSERT INTO dq_test_log(run_at, test_no, test_name, status, details)
    VALUES (v_run_at, 9, 'Date range check', 'INFO',
            format('min_date=%s max_date=%s distinct_days=%s', v_min_date, v_max_date, v_distinct_days));

    ---------------------------------------------------------------
    -- TEST 10: pickup/drop location referential check
    ---------------------------------------------------------------
    FOR r IN
        SELECT 'pickup' AS role, COUNT(*) AS unmatched
        FROM fact_bookings f
        LEFT JOIN dim_location l ON l.location_key = f.pickup_location_key
        WHERE f.pickup_location_key IS NOT NULL AND l.location_key IS NULL

        UNION ALL

        SELECT 'drop', COUNT(*)
        FROM fact_bookings f
        LEFT JOIN dim_location l ON l.location_key = f.drop_location_key
        WHERE f.drop_location_key IS NOT NULL AND l.location_key IS NULL
    LOOP
        INSERT INTO dq_test_log(run_at, test_no, test_name, status, details)
        VALUES (v_run_at, 10, format('Location referential: %s', r.role),
                CASE WHEN r.unmatched = 0 THEN 'PASS' ELSE 'FAIL' END,
                format('unmatched_count=%s', r.unmatched));
    END LOOP;

    RAISE NOTICE 'Data quality tests complete. run_at = %', v_run_at;

END;
$$;