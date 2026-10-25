# Contributing

1. Create a focused branch from `main`.
2. Do not add credentials, private datasets, generated logs, dbt `target/` output, or model weights.
3. Preserve existing Snowflake, dbt, Airflow, and AI behavior unless the change explicitly targets functionality.
4. Run relevant local syntax or documentation checks.
5. Review staged files and diffs before committing.
6. Use Conventional Commit titles such as `docs: improve local setup instructions` or `test(dbt): add order integrity checks`.

Changes requiring Snowflake credentials, AWS access, Ollama models, or live infrastructure should document the limitation and include offline validation where practical.
