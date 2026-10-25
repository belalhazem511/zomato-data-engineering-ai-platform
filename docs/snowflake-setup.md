# Snowflake setup

The implementation expects database `ZOMATO`, schemas `RAW`, `STAGING`, `MARTS`, and `AI`, warehouse `ZOMATO_WH`, and external stage `ZOMATO.RAW.ZOMATO_RAW_STAGE`.

Required environment variables are documented in `airflow/.env.example` and `ai/.env.example`. Values must be supplied locally and must not be committed.

The Airflow connection is assembled from environment variables in `airflow/docker-compose.yaml`. dbt reads the same account, user, and password variables through `profiles.yml`.

For Text-to-SQL, create and configure a dedicated read-only role before enabling execution. The current fallback to `DBT_ROLE` is a known security risk.

The repository does not provide DDL for the existing Snowflake database, stage, storage integration, or file formats. Those objects must be provisioned separately by an authorized administrator.
