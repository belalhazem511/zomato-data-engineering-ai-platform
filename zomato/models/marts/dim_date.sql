
{{ config(materialized='table') }}

WITH spine AS (
    SELECT
        DATEADD(
            day,
            ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1,
            '2024-01-01'::DATE
        ) AS date_day
    FROM TABLE(GENERATOR(ROWCOUNT => 1200))
)

SELECT
    date_day,
    YEAR(date_day) AS year,
    QUARTER(date_day) AS quarter,
    MONTH(date_day) AS month,
    MONTHNAME(date_day) AS month_name,
    DAY(date_day) AS day_of_month,
    DAYNAME(date_day) AS day_name,
    DAYOFWEEKISO(date_day) AS day_of_week,
    DAYOFWEEKISO(date_day) >= 6 AS is_weekend
FROM spine
WHERE date_day <= '2026-12-31'::DATE
