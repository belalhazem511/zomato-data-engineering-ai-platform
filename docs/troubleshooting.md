# Troubleshooting

## Airflow cannot connect to Snowflake

Check the local `airflow/.env`, the Airflow connection environment variable, account identifier, role, warehouse, and network access. Do not print credentials while debugging.

## dbt cannot find a profile

Run dbt with the project directory as both `--project-dir` and `--profiles-dir`, as the DAG does. Confirm the required Snowflake environment variables are set.

## RAW load processes zero files

This can be normal when Snowflake has already consumed the staged files. Inspect Snowflake load history with an authorized diagnostic process.

## Enrichment fails while importing Transformers

The Airflow image installs Transformers and CPU PyTorch in the Dockerfile. Rebuild only when dependencies changed, and avoid deleting volumes.

## Ollama errors

Confirm Ollama is running locally and that the requested Qwen2.5 model is installed. The RAG and Text-to-SQL applications use different model tags.

## Text-to-SQL query failures

Compare generated SQL with the actual dbt MARTS relations. The current application schema is known to be out of sync with several model names and columns.
