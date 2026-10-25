"""Small, mockable read-only query execution primitive."""

from __future__ import annotations

try:
    from .text_to_sql_validation import bounded_query
except ImportError:
    from text_to_sql_validation import bounded_query


def execute_dataframe(connection, sql: str, max_rows: int):
    """Execute a pre-validated query through an existing Snowflake connection."""

    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(bounded_query(sql, max_rows))
        return cursor.fetch_pandas_all()
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
