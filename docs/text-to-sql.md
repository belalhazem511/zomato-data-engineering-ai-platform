# Text-to-SQL

`ai/text_to_sql.py` uses local Ollama model `qwen2.5:1.5b` to generate one JSON object containing SQL. SQLGlot parses the result using Snowflake syntax.

Validation currently checks one statement, SELECT or UNION shape, forbidden write/DDL operations, unqualified table names, and table allowlisting.

Execution wraps the validated query with a 100-row limit and requires a Streamlit button click. A dedicated read-only Snowflake role is still required. The current prompt schema and allowlist must be reconciled with the actual dbt mart names and columns before production use.
