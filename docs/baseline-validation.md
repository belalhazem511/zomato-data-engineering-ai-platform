# Improvement baseline

Captured on the `feature/zomato-platform-improvements` branch before feature work.

## Repository state

- `main` matched `origin/main` at commit `c4eb85f`.
- Working tree was clean.
- Airflow and dbt source files were reviewed and protected with baseline hashes.
- No Snowflake, Airflow, Docker runtime, or historical enrichment operation was executed.

## Local checks

| Check | Result | Notes |
| --- | --- | --- |
| Python syntax compilation | Pass | All current files under `ai/` compiled successfully. |
| Docker Compose static validation | Pass | `docker compose config --no-interpolate --quiet`. |
| Existing complaint-rule test | Not run | Host lacks `snowflake.connector`; the script imports runtime dependencies before `--test`. |
| dbt execution | Not run | Would require live Snowflake access. |
| Airflow execution | Not run | Existing successful execution is documented in repository history/log evidence. |

## Available host dependencies

Available: Pandas, Requests, NumPy.

Unavailable: Snowflake connector, python-dotenv, Transformers, Sentence Transformers, Streamlit, and SQLGlot.

New tests are therefore designed around dependency-light helpers wherever possible. Tests requiring SQLGlot or application runtimes are explicitly marked as unavailable rather than being represented as live integration success.
