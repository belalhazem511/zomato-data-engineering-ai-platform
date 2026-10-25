
import os
import json

import pandas as pd
import requests
import streamlit as st
import snowflake.connector
from dotenv import load_dotenv
from sqlglot import parse, exp

load_dotenv()

MODEL = "qwen2.5:1.5b"
OLLAMA_URL = "http://localhost:11434/api/generate"
MAX_ROWS = 100

ALLOWED_TABLES = {
    "FCT_ORDERS",
    "DIM_RESTAURANT",
    "DIM_CUSTOMER",
    "MART_DAILY_CITY_REVENUNE",
    "MART_RESTAURANT_PERFORMANCE",
    "MART_DELIVERY_SLA",
}

EXAMPLE_QUESTIONS = [
    "Top 10 cities by GMV",
    "Which cuisine has the most orders?",
    "Average delivery time by city, worst first",
    "Cancel rate by payment method",
]

SCHEMA = """
Snowflake tables available in the MARTS schema:

FCT_ORDERS(
    order_id, order_date, customer_id,
    restaurant_id, city, cuisine,
    payment_method, order_status,
    is_delivered, sales_amount,
    discount, delivery_fee, gst,
    customer_rating, delivery_time_min
)

DIM_RESTAURANT(
    restaurant_id, restaurant_name,
    city, cuisine, rating, cost_for_two
)

DIM_CUSTOMER(
    customer_id, customer_name,
    age, age_segment, gender, city
)

MART_DAILY_CITY_REVENUNE(
    order_date, city, orders,
    cancel_rate, gmv, aov
)

MART_RESTAURANT_PERFORMANCE(
    restaurant_id, restaurant_name,
    city, cuisine, orders, revenue,
    avg_customer_rating, cancel_rate
)

MART_DELIVERY_SLA(
    city, order_hour, delivered_orders,
    p50_delivery_min, late_rate
)

Important:
- GMV means delivered revenue.
- Prefer MART tables when appropriate.
- Use only listed tables and columns.
- Tables are in the current MARTS schema.
- Use bare table names.
"""

SYSTEM_PROMPT = f"""
You are an expert Snowflake SQL data analyst.

Convert the user's English question into ONE
valid Snowflake SQL SELECT query.

Rules:
1. Return a JSON object with exactly one key: "sql".
2. Generate SELECT statements only.
3. Use only tables and columns from the schema.
4. Never invent columns.
5. Do not use database or schema prefixes.
6. Prefer existing MART tables for aggregates.
7. Use correct Snowflake syntax.
8. Use NULLIF when dividing by a possibly zero value.
9. Never modify database objects or data.
10. For rankings, use ORDER BY and LIMIT.
11. Do not make up results or numeric values.
12. If the question cannot be answered using
    the provided schema, return {{"sql": ""}}.

Database schema:
{SCHEMA}

Example:
Question: Top 10 cities by GMV

Response:
{{
  "sql": "SELECT city, SUM(gmv) AS total_gmv FROM MART_DAILY_CITY_REVENUNE GROUP BY city ORDER BY total_gmv DESC LIMIT 10"
}}
"""


def get_connection():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv(
            "SNOWFLAKE_WAREHOUSE", "ZOMATO_WH"
        ),
        database=os.getenv(
            "SNOWFLAKE_DATABASE", "ZOMATO"
        ),
        schema="MARTS",
        role=os.getenv(
            "SNOWFLAKE_READONLY_ROLE", "DBT_ROLE"
        ),
        session_parameters={
            "STATEMENT_TIMEOUT_IN_SECONDS": 60
        }
    )


def generate_sql(question):
    prompt = (
        SYSTEM_PROMPT
        + "\n\nUser question:\n"
        + question
        + "\n\nReturn JSON only."
    )

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 500
            }
        },
        timeout=300
    )

    response.raise_for_status()

    raw_answer = response.json()["response"]
    result = json.loads(raw_answer)

    sql = result.get("sql", "")

    if not isinstance(sql, str):
        raise ValueError(
            "Model returned an invalid SQL value."
        )

    return sql.strip().rstrip(";")


def validate_sql(sql):
    if not sql:
        raise ValueError(
            "The question cannot be answered "
            "using the available schema."
        )

    statements = parse(sql, read="snowflake")

    if len(statements) != 1:
        raise ValueError(
            "Only one SQL statement is allowed."
        )

    tree = statements[0]

    if not isinstance(tree, (exp.Select, exp.Union)):
        raise ValueError(
            "Only read-only SELECT queries are allowed."
        )

    forbidden_types = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.Merge,
        exp.Command,
        exp.Into,
    )

    for node in tree.walk():
        if isinstance(node, forbidden_types):
            raise ValueError(
                "SQL contains a forbidden operation."
            )

    cte_names = {
        cte.alias_or_name.upper()
        for cte in tree.find_all(exp.CTE)
    }

    tables = list(tree.find_all(exp.Table))

    if not tables:
        raise ValueError(
            "SQL must query an approved table."
        )

    used_approved_table = False

    for table in tables:
        name = table.name.upper()

        if table.db or table.catalog:
            raise ValueError(
                "Qualified table names are not allowed."
            )

        if name in cte_names:
            continue

        if name not in ALLOWED_TABLES:
            raise ValueError(
                f"Table {name} is not allowed."
            )

        used_approved_table = True

    if not used_approved_table:
        raise ValueError(
            "No approved data table was referenced."
        )

    return tree.sql(dialect="snowflake")


def run_query(sql):
    # Apply a maximum result size,
    # even if the LLM omits LIMIT.
    limited_sql = f"""
        SELECT *
        FROM ({sql}) AS SAFE_RESULT
        LIMIT {MAX_ROWS}
    """

    conn = get_connection()
    cursor = None

    try:
        cursor = conn.cursor()
        cursor.execute(limited_sql)
        return cursor.fetch_pandas_all()

    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


# ---------------- UI ----------------

st.set_page_config(
    page_title="Zomato Text-to-SQL",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Chat with Your Zomato Data")

st.caption(
    f"Local Ollama ({MODEL}) + "
    "Snowflake SQL Analytics"
)

with st.sidebar:
    st.header("Example Questions")

    for example in EXAMPLE_QUESTIONS:
        st.write(f"• {example}")

    st.divider()

    st.info(
        "SQL is generated locally. "
        "Results come from Snowflake."
    )

question = st.text_input(
    "Ask a question about your data:",
    placeholder="Top 10 cities by GMV"
)

if question.strip():

    with st.spinner("Generating Snowflake SQL..."):
        try:
            generated_sql = generate_sql(question)

            safe_sql = validate_sql(
                generated_sql
            )

        except requests.exceptions.RequestException:
            st.error(
                "Ollama is unavailable. "
                "Check that Ollama is running "
                "and the selected model exists."
            )
            st.stop()

        except (ValueError, json.JSONDecodeError) as error:
            st.error(str(error))
            st.stop()

    st.subheader("Generated SQL")
    st.code(safe_sql, language="sql")

    # Require user approval before execution.
    if st.button(
        "Run SQL in Snowflake",
        type="primary"
    ):

        with st.spinner("Running Snowflake query..."):
            try:
                df = run_query(safe_sql)

                st.success(
                    f"Query completed: {len(df)} rows."
                )

                st.dataframe(
                    df,
                    hide_index=True,
                    use_container_width=True
                )

                if (
                    len(df.columns) == 2
                    and pd.api.types.is_numeric_dtype(
                        df.iloc[:, 1]
                    )
                ):
                    st.bar_chart(
                        df,
                        x=df.columns[0],
                        y=df.columns[1]
                    )

                st.download_button(
                    "Download CSV",
                    data=df.to_csv(index=False),
                    file_name="zomato_query_results.csv",
                    mime="text/csv"
                )

            except Exception as error:
                st.error(
                    f"Snowflake query failed: {error}"
                )
