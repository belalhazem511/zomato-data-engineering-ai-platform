"""Dependency-light schema and SQL safety helpers for the Text-to-SQL app."""

from __future__ import annotations


# These columns mirror the current dbt models under zomato/models/marts.
# Keep the existing MART_DAILY_CITY_REVENUNE spelling for compatibility.
TABLE_SCHEMAS = {
    "FCT_ORDERS": (
        "order_id", "order_timestamp", "order_date", "customer_id",
        "restaurant_id", "city", "cuisine", "payment_method",
        "order_status", "is_delivered", "items_count", "sales_qty",
        "subtotal", "discount", "delivery_fee", "gst", "sales_amount",
        "customer_rating", "delivery_time_min",
    ),
    "FACT_ORDER_ITEMS": (
        "order_item_id", "order_id", "restaurant_id", "f_id", "order_ts",
        "order_date", "city", "price", "quantity", "line_amount",
    ),
    "DIM_RESTAURANTS": (
        "restaurant_id", "restaurant_name", "city", "cuisine", "rating",
        "rating_count", "cost_for_two",
    ),
    "DIM_CUSTOMER": (
        "customer_id", "customer_name", "email", "age", "age_segment",
        "gender", "marital_status", "occupation", "income_band",
        "education", "family_size",
    ),
    "DIM_FOOD": ("f_id", "food_name", "veg_or_non_veg"),
    "DIM_DATE": (
        "date_day", "year", "quarter", "month", "month_name",
        "day_of_month", "day_name", "day_of_week", "is_weekend",
    ),
    "MART_DAILY_CITY_REVENUNE": (
        "order_date", "city", "orders", "delivered_orders", "cancel_rate",
        "gmv", "aov",
    ),
    "MART_RESTAURANT_PERFORMANCE": (
        "restaurant_id", "restaurant_name", "city", "cuisine", "orders",
        "revenue", "avg_customer_rating", "avg_delivery_min",
    ),
    "MART_DELIVERY_SLA": (
        "city", "order_hour", "delivered_orders", "p50", "p90",
    ),
}

ALLOWED_TABLES = frozenset(TABLE_SCHEMAS)


def schema_prompt() -> str:
    """Render the allowlisted dbt schema for the local model prompt."""

    lines = ["Snowflake tables available in the MARTS schema:", ""]
    for table, columns in TABLE_SCHEMAS.items():
        lines.append(f"{table}(")
        lines.append("    " + ", ".join(columns))
        lines.append(")")
        lines.append("")

    lines.extend(
        [
            "Important:",
            "- GMV means delivered revenue.",
            "- Prefer MART tables when appropriate.",
            "- Use only listed tables and columns.",
            "- Tables are in the current MARTS schema.",
            "- Use bare table names.",
        ]
    )
    return "\n".join(lines)


def required_read_only_role() -> str:
    """Return the explicitly configured execution role or fail closed."""

    import os

    role = os.getenv("SNOWFLAKE_READONLY_ROLE", "").strip()
    if not role:
        raise RuntimeError(
            "SNOWFLAKE_READONLY_ROLE must be configured; refusing to execute SQL "
            "with a potentially privileged fallback role."
        )
    return role


def bounded_query(sql: str, max_rows: int) -> str:
    """Wrap a validated query with a positive hard result limit."""

    if not isinstance(max_rows, int) or max_rows <= 0:
        raise ValueError("max_rows must be a positive integer.")
    return f"SELECT * FROM ({sql}) AS SAFE_RESULT LIMIT {max_rows}"


def _sqlglot_modules():
    try:
        from sqlglot import exp, parse
    except ImportError as error:
        raise RuntimeError(
            "SQLGlot is required to validate generated SQL before execution."
        ) from error
    return exp, parse


def _forbidden_expression_types(exp):
    names = (
        "Insert", "Update", "Delete", "Drop", "Create", "Alter", "Merge",
        "Command", "Into", "Truncate", "Grant", "Revoke",
    )
    return tuple(
        expression_type
        for name in names
        if (expression_type := getattr(exp, name, None)) is not None
    )


def _validate_columns(tree, exp, table_schemas, cte_names):
    aliases = {
        alias.alias.upper()
        for alias in tree.find_all(exp.Alias)
        if alias.alias
    }

    for column in tree.find_all(exp.Column):
        name = column.name.upper()
        if name == "*":
            continue

        qualifier = column.table.upper() if column.table else ""
        if qualifier in cte_names:
            continue

        if qualifier:
            schema = table_schemas.get(qualifier)
            if schema is None:
                raise ValueError(
                    f"Column qualifier {qualifier} is not an approved table alias."
                )
            if name not in schema:
                raise ValueError(
                    f"Column {name} does not exist on approved table alias {qualifier}."
                )
            continue

        if name in aliases:
            continue
        if not any(name in schema for schema in table_schemas.values()):
            raise ValueError(f"Column {name} is not in the approved dbt schema.")


def validate_sql(sql: str) -> str:
    """Parse and validate one read-only query against the dbt mart contract."""

    if not isinstance(sql, str) or not sql.strip():
        raise ValueError(
            "The question cannot be answered using the available schema."
        )

    exp, parse = _sqlglot_modules()
    statements = parse(sql.strip().rstrip(";"), read="snowflake")
    if len(statements) != 1:
        raise ValueError("Only one SQL statement is allowed.")

    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union)):
        raise ValueError("Only read-only SELECT queries are allowed.")

    forbidden_types = _forbidden_expression_types(exp)
    if any(isinstance(node, forbidden_types) for node in tree.walk()):
        raise ValueError("SQL contains a forbidden write or DDL operation.")

    cte_names = {
        cte.alias_or_name.upper()
        for cte in tree.find_all(exp.CTE)
    }
    table_schemas = {}
    approved_table_found = False

    for table in tree.find_all(exp.Table):
        name = table.name.upper()
        if name in cte_names:
            continue
        if table.db or table.catalog:
            raise ValueError(
                "Qualified table names are not allowed; query MARTS tables by name."
            )
        if name not in ALLOWED_TABLES:
            raise ValueError(f"Table {name} is not allowed.")

        approved_table_found = True
        schema = set(column.upper() for column in TABLE_SCHEMAS[name])
        table_schemas[name] = schema
        table_schemas[table.alias_or_name.upper()] = schema

    if not approved_table_found:
        raise ValueError("SQL must query at least one approved dbt mart table.")

    _validate_columns(tree, exp, table_schemas, cte_names)
    return tree.sql(dialect="snowflake")
