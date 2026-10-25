# Local development

Create a Python virtual environment and install `requirements-ai.txt` for the Streamlit applications. Copy the relevant `.env.example` file to `.env` and fill it locally.

Start Ollama separately, then pull `qwen2.5:3b` and `qwen2.5:1.5b` as needed. The RAG and Text-to-SQL apps use `http://localhost:11434/api/generate`.

Airflow development runs from `airflow/` with Docker Compose. dbt is executed inside the Airflow image or against a separately configured local dbt environment.

Start the analytics dashboard with `streamlit run dashboard/app.py`. It shares the AI application's Snowflake environment variables and requires an explicit `SNOWFLAKE_READONLY_ROLE`.

Raw `Data/*.csv` files are intentionally not part of the public repository. Use authorized data and the documented source headers in `Data/README.md`.
