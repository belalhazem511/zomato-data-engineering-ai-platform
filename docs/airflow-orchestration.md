# Airflow orchestration

Airflow 3.0.3 runs with Docker Compose, LocalExecutor, PostgreSQL metadata storage, a dedicated API server, scheduler, and DAG processor.

The DAG is defined in `airflow/dags/zomato_batch.py`. dbt is installed in `/opt/airflow/dbt_venv`, while the dbt project and AI code are mounted from the host.

The latest inspected logs show successful completion of all four task commands. Historical logs are retained locally but excluded from Git.

Do not use `docker compose down -v` unless you explicitly intend to remove local Airflow metadata volumes.
