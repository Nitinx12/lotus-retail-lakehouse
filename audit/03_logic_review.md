# 03 Logic review

Evidence comes from the live runs in `02_execution_log.md` plus code reading. Row counts: bronze 42,877 in, silver 42,827 out (50 customer rows removed), gold facts 12,000 orders plus 25,099 details plus 1,056 returns, published totals match.

## 1. Silently lost or duplicated rows at layer boundaries

Loss is accounted for, duplication is absent, with two qualifications.

Bronze to silver drops exactly 50 rows, all in `dim_customers` (3,050 to 3,000). The log attributes this to the null key drop plus natural key dedupe. No other table loses rows. The qualification: dedupe keeps the first row while the downstream SCD2 keeps the last, and the drop runs before the null key filter, so which duplicate survives is order dependent. Counts reconcile, identity of survivors is not proven.

Silver to gold preserves every fact (12,000 in, 12,000 out, 0 duplicated order ids in the scenario join). The point in time join keeps orphans with null keys instead of dropping them; live published data has 0 null customer keys and 0 dangling keys.

Gold to Postgres preserves counts (publish log total 42,827). dbt marts reconcile exactly on revenue (45,350,979.0 on both sides).

The blind spot is the union of the two order files: overlapping order ids resolve silently in favor of 2022 2023 with no collision count. If the two source files ever share an id, one row vanishes without a log line. No overlap was measured live.

## 2. Metric definitions across Spark marts, dbt marts, Streamlit, R

Revenue is gross shipped revenue everywhere: `sum(total_revenue)` in `src/gold/build.py:64`, `sum(total_revenue::NUMERIC)` in the dbt mart, and the two agree to the decimal (45,350,979.0). Returns are never netted, and no discount, tax, or currency treatment exists anywhere. `EGP` is a display prefix only. Whether gross is correct is a business decision, but it is at least consistent. The Spark parquet mart is never published and the quality gate checks that unpublished copy while the dashboard and R read the dbt copy, so consistency today rests on the two builders staying identical by hand.

Return rate is order granular in both builders: one returned order flags every detail line on that order, denominator is detail lines. Multi item orders inflate the product rate. Both builders share the flaw, so they agree numerically, but the number does not mean what its name says.

Ramadan has two provenances. The dbt mart trusts `dim_date.is_ramadan`, which no code sets; the flag arrives from the Mongo seed untouched. The dashboard and R retag months from hardcoded per year ranges and ignore the mart column. The 2024 range ends 04-08 in both UI and R copies, one day before the observed Egyptian end of Ramadan. The ranges themselves are correct per year shape (not a fixed month bug), but the single day boundary and the dual provenance need a human ruling.

## 3. Dates and timezones

Business dates are naive throughout Silver and Gold. Guards compare against server `CURRENT_DATE`. Freshness uses UTC in the dashboard against a 24 hour sliding window, while the spec promises 7 AM IST. The Airflow schedule is a naive `@daily` (midnight UTC, 05:30 IST), leaving about 90 minutes to the stated SLA against a 215 minute serial path. No `Africa/Cairo` conversion exists anywhere. Ramadan ranges are date only strings, immune to timezones, but the SLA and freshness story disagrees with itself in three places (spec, dashboard constant, schedule).

## 4. Money precision

Python facts are float64, published by `to_sql` inference into float columns, and the C# fact models mirror that with `double?`. dbt casts to NUMERIC at mart read time, which is why the marts reconcile exactly today. The fact layer itself can accumulate binary float error, and the C# detail model types price and discount percent as long, losing fractions. Mart level numbers are safe, fact level storage is not.

## 5. Join safety

The returns enrichment is fan out safe (grouped to one row per order before the left join, orphans flagged). The customer and employee point in time joins preserve orphans and produced no duplicates on 12,000 live facts. Two gaps: overlapping dimension versions would fan out facts with no guard or assertion, and the order union plus the returns orphan check ignore product grain (order id only), so a return for product A on an order also containing product B is indistinguishable at line grain.

## 6. Rerun, backfill, partial failure states

Reruns are content stable (byte identical excluding run tags across three runs). SCD2 reruns add no versions. Missing bronze files trigger reload. The inconsistent states that survive undetected: a same count content change in Mongo is skipped silently; a new column on existing documents never fires the schema logger for the same reason; `main.py all` never runs the GX gates, so a green full run can skip quality entirely; publish commits eight tables in eight transactions, so a crash mid loop leaves split versions with no marker; failed ops rows carry NULL `ended_at`, so failure age and duration math is void; retry attempts overwrite each other under the run plus task key, so the second retry erases the first.

## 7. Monitoring truthfulness

Row counts are real per task writes and the ops page trends them. Quality percents are real gate outputs. Freshness reads a real timestamp but judges it against the wrong SLA (24 h vs 7 AM IST). Durations are fiction (all zeros) for the transaction timestamp reason. Alerts fire correctly on failed runs and on quality drops through the trigger path; delivery beyond the database (Slack, PagerDuty) is stubbed. The R report can render random demo data when the warehouse password is absent, which would put plausible looking but fake numbers into a PDF with no watermark of their origin.
