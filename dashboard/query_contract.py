"""Read-only dashboard query contracts based on the current dbt marts."""

from __future__ import annotations


MART_TABLES = {
    "MART_DAILY_CITY_REVENUNE",
    "MART_RESTAURANT_PERFORMANCE",
    "MART_DELIVERY_SLA",
    "FCT_ORDERS",
    "DIM_CUSTOMER",
    "MART_REVIEW_INSIGHTS",
}


def build_order_filters(city=None, start_date=None, end_date=None, alias=""):
    """Build a parameterized filter fragment for order-backed marts."""

    prefix = f"{alias}." if alias else ""
    clauses = []
    params = []
    if city:
        clauses.append(f"{prefix}city = %s")
        params.append(city)
    if start_date:
        clauses.append(f"{prefix}order_date >= %s")
        params.append(start_date)
    if end_date:
        clauses.append(f"{prefix}order_date <= %s")
        params.append(end_date)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", tuple(params)


EXECUTIVE_QUERY = """
SELECT
    COALESCE(SUM(gmv), 0) AS total_gmv,
    COALESCE(SUM(orders), 0) AS total_orders,
    COALESCE(SUM(gmv) / NULLIF(SUM(delivered_orders), 0), 0) AS average_order_value,
    COALESCE(SUM(cancel_rate * orders) / NULLIF(SUM(orders), 0), 0) AS cancellation_rate
FROM MART_DAILY_CITY_REVENUNE
"""

REVENUE_BY_CITY_QUERY = """
SELECT city, order_date, orders, delivered_orders, cancel_rate, gmv, aov
FROM MART_DAILY_CITY_REVENUNE
"""

TOP_RESTAURANTS_QUERY = """
SELECT restaurant_id, restaurant_name, city, cuisine, orders, revenue,
       avg_customer_rating, avg_delivery_min
FROM MART_RESTAURANT_PERFORMANCE
"""

DELIVERY_QUERY = """
SELECT city, order_hour, delivered_orders, p50, p90
FROM MART_DELIVERY_SLA
"""

CUSTOMER_QUERY = """
SELECT c.age_segment, COUNT(DISTINCT f.customer_id) AS customers,
       COUNT(*) AS orders
FROM FCT_ORDERS f
LEFT JOIN DIM_CUSTOMER c ON f.customer_id = c.customer_id
"""

REVIEW_QUERY = """
SELECT city, topic, sentiment_label, reviews, avg_sentiment_score,
       avg_star_rating, flagged_issues
FROM MART_REVIEW_INSIGHTS
"""
