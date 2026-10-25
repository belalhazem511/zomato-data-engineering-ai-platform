# dbt models

## Staging

- `stg_users`: normalizes customer identifiers and demographic fields.
- `stg_restaurants`: parses restaurant IDs, cities, ratings, rating counts, and costs.
- `stg_food`: normalizes food names and vegetarian classification.
- `stg_menu`: normalizes menu IDs, restaurant IDs, food IDs, cuisine, and prices.
- `stg_orders`: standardizes order identifiers, dates, financials, status, and delivery metrics.
- `stg_order_items`: standardizes order-item identifiers, prices, quantities, and line amounts.
- `stg_reviews`: filters empty comments and adds restaurant city.

## Marts

- `dim_customer`, `dim_restaurants`, `dim_food`, `dim_date`: dimensions.
- `fct_orders`: incremental order fact keyed by `order_id`.
- `fact_order_items`: incremental order-item fact keyed by `order_item_id`.
- `mart_daily_city_revenune`: city/day order, cancellation, GMV, and AOV metrics. The spelling is preserved from the current model.
- `mart_restaurant_performance`: restaurant order, revenue, rating, and delivery metrics.
- `mart_delivery_sla`: delivered-order counts and p50/p90 delivery metrics by city and hour.
- `mart_review_insights`: AI sentiment/topic aggregates by city.

Core tests cover key uniqueness, non-null constraints, accepted order statuses, and relationships. The latest logged core build reported 40 passes and no warnings or errors.
