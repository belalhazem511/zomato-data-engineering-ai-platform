
FROM apache/airflow:3.0.3

# Airflow and Snowflake dependencies
RUN pip install --no-cache-dir \
    apache-airflow-providers-snowflake \
    apache-airflow-providers-fab \
    snowflake-connector-python \
    "transformers>=4.44,<5"

# CPU-only PyTorch
RUN pip install --no-cache-dir \
    torch \
    --index-url https://download.pytorch.org/whl/cpu

# Isolated dbt environment
RUN python -m venv /opt/airflow/dbt_venv && \
    /opt/airflow/dbt_venv/bin/pip install --no-cache-dir \
    "dbt-snowflake==1.8.*"
