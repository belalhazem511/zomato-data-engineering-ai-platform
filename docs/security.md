# Security

Never commit `.env` files, `creds`, Snowflake passwords, AWS credentials, API keys, tokens, private keys, logs, dbt artifacts, model caches, or raw datasets.

The repository `.gitignore` excludes these classes of files. Always review `git diff --cached` before each commit.

Raw local data is excluded because it contains potentially personal information and redistribution rights are unknown. The source includes user identity fields and restaurant addresses.

Use a dedicated read-only role for Text-to-SQL. The current application falls back to `DBT_ROLE` when `SNOWFLAKE_READONLY_ROLE` is absent; this must be resolved before production use.

Development Airflow credentials and placeholder secrets in Compose are not production-safe. Use externally managed secrets for shared deployments.
