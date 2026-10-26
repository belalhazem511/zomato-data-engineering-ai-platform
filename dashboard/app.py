"""Read-only Streamlit analytics dashboard for the current Zomato marts."""

from __future__ import annotations

import os

import pandas as pd
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv

try:
    from .query_contract import (
        CUSTOMER_QUERY,
        DELIVERY_QUERY,
        EXECUTIVE_QUERY,
        MART_TABLES,
        REVENUE_BY_CITY_QUERY,
        REVIEW_QUERY,
        TOP_RESTAURANTS_QUERY,
        build_order_filters,
    )
except ImportError:
    from query_contract import (
        CUSTOMER_QUERY,
        DELIVERY_QUERY,
        EXECUTIVE_QUERY,
        MART_TABLES,
        REVENUE_BY_CITY_QUERY,
        REVIEW_QUERY,
        TOP_RESTAURANTS_QUERY,
        build_order_filters,
    )


load_dotenv()

st.set_page_config(
    page_title="Zomato Analytics Dashboard",
    page_icon="📊",
    layout="wide",
)


def get_connection():
    role = os.getenv("SNOWFLAKE_READONLY_ROLE", "").strip()
    if not role:
        raise RuntimeError(
            "SNOWFLAKE_READONLY_ROLE must be configured for the dashboard."
        )
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "ZOMATO_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "ZOMATO"),
        schema="MARTS",
        role=role,
        session_parameters={"STATEMENT_TIMEOUT_IN_SECONDS": 60},
    )


@st.cache_data(ttl=600, show_spinner=False)
def read_query(sql, params=()):
    """Execute one fixed read-only query and return a lowercase DataFrame."""

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        frame = cursor.fetch_pandas_all()
        frame.columns = [column.lower() for column in frame.columns]
        return frame
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def show_empty(frame, message):
    if frame.empty:
        st.info(message)
        return True
    return False


def render_filters(revenue_frame):
    cities = sorted(
        value for value in revenue_frame["city"].dropna().unique().tolist()
    )
    city = st.sidebar.selectbox("City", ["All cities"] + cities)
    city_value = None if city == "All cities" else city

    min_date = revenue_frame["order_date"].min()
    max_date = revenue_frame["order_date"].max()
    date_range = st.sidebar.date_input(
        "Order date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range
    return city_value, start_date, end_date


def main():
    st.title("Zomato Analytics Dashboard")
    st.caption(
        "Read-only analytics over the dbt MARTS and AI review-insights models."
    )

    with st.spinner("Loading analytics marts..."):
        try:
            revenue_frame = read_query(REVENUE_BY_CITY_QUERY)
        except Exception as error:
            st.error(f"Unable to load Snowflake analytics: {error}")
            st.info(
                "Configure Snowflake credentials and SNOWFLAKE_READONLY_ROLE, "
                "then retry the dashboard."
            )
            return

    if show_empty(revenue_frame, "No revenue records are available for the dashboard."):
        return

    city, start_date, end_date = render_filters(revenue_frame)
    revenue_filter, revenue_params = build_order_filters(
        city, start_date, end_date
    )
    filtered_revenue = read_query(
        REVENUE_BY_CITY_QUERY + revenue_filter,
        revenue_params,
    )
    if show_empty(filtered_revenue, "No records match the selected filters."):
        return

    st.subheader("Executive overview")
    total_gmv = filtered_revenue["gmv"].sum()
    total_orders = filtered_revenue["orders"].sum()
    delivered_orders = filtered_revenue["delivered_orders"].sum()
    average_order_value = total_gmv / delivered_orders if delivered_orders else 0
    cancellation_rate = (
        (filtered_revenue["cancel_rate"] * filtered_revenue["orders"]).sum()
        / total_orders
        if total_orders
        else 0
    )
    metrics = st.columns(4)
    metrics[0].metric("Total GMV", f"{total_gmv:,.2f}")
    metrics[1].metric("Total orders", f"{total_orders:,.0f}")
    metrics[2].metric("Average order value", f"{average_order_value:,.2f}")
    metrics[3].metric("Cancellation rate", f"{cancellation_rate:.2%}")

    with st.spinner("Loading supporting marts..."):
        try:
            restaurant_frame = read_query(TOP_RESTAURANTS_QUERY)
            delivery_frame = read_query(DELIVERY_QUERY)
            customer_frame = read_query(
                CUSTOMER_QUERY + " GROUP BY c.age_segment ORDER BY orders DESC"
            )
            review_frame = read_query(REVIEW_QUERY)
        except Exception as error:
            st.error(f"Unable to load one or more analytics sections: {error}")
            return

    revenue_tab, delivery_tab, customer_tab, review_tab = st.tabs(
        ["Revenue", "Orders & delivery", "Customers", "AI review insights"]
    )

    with revenue_tab:
        st.subheader("Revenue analytics")
        daily = filtered_revenue.groupby("order_date", as_index=False)["gmv"].sum()
        st.line_chart(daily.set_index("order_date"), y="gmv")
        city_revenue = filtered_revenue.groupby("city", as_index=False)["gmv"].sum()
        st.bar_chart(city_revenue.set_index("city"), y="gmv")
        if not show_empty(restaurant_frame, "No restaurant performance data is available."):
            st.dataframe(
                restaurant_frame.sort_values("revenue", ascending=False).head(10),
                hide_index=True,
                use_container_width=True,
            )

    with delivery_tab:
        st.subheader("Order and delivery analytics")
        st.line_chart(filtered_revenue.set_index("order_date")["orders"])
        cancel_trend = filtered_revenue[["order_date", "cancel_rate"]].copy()
        st.line_chart(cancel_trend.groupby("order_date").mean())
        if not show_empty(delivery_frame, "No delivery SLA data is available."):
            st.dataframe(delivery_frame, hide_index=True, use_container_width=True)

    with customer_tab:
        st.subheader("Customer analytics")
        if not show_empty(customer_frame, "No customer ordering data is available."):
            st.bar_chart(customer_frame.set_index("age_segment")["orders"])
            st.dataframe(customer_frame, hide_index=True, use_container_width=True)

    with review_tab:
        st.subheader("AI review insights")
        if not show_empty(review_frame, "No AI review insights are available."):
            sentiment = review_frame.groupby("sentiment_label", as_index=False)["reviews"].sum()
            topics = review_frame.groupby("topic", as_index=False)["reviews"].sum()
            st.bar_chart(sentiment.set_index("sentiment_label"), y="reviews")
            st.bar_chart(topics.set_index("topic"), y="reviews")
            st.dataframe(review_frame, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
