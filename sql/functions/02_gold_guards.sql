-- rejects future order dates and negative revenue on facts
CREATE OR REPLACE FUNCTION gold.guard_fact_order()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.order_date::DATE > CURRENT_DATE THEN
        RAISE EXCEPTION 'future order_date % rejected', NEW.order_date;
    END IF;
    IF NEW.total_revenue::NUMERIC < 0 THEN
        RAISE EXCEPTION 'negative total_revenue rejected for order %', NEW.order_id;
    END IF;
    RETURN NEW;
END
$$;

-- rejects negative return amounts on facts
CREATE OR REPLACE FUNCTION gold.guard_fact_return()
RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.return_amount::NUMERIC < 0 THEN
        RAISE EXCEPTION 'negative return_amount rejected for return %', NEW.return_id;
    END IF;
    RETURN NEW;
END
$$;
