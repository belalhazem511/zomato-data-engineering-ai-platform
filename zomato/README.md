# Zomato dbt project

This directory contains the dbt transformation project for the Zomato analytics platform.

- `models/staging/` contains normalized views over `ZOMATO.RAW`.
- `models/marts/` contains dimensions, facts, business marts, and the AI review mart.
- `profiles.yml` reads Snowflake credentials from environment variables.
- `dbt_project.yml` configures staging views and mart tables.

See the repository root README and [`docs/dbt-models.md`](../docs/dbt-models.md) for setup and model lineage.
