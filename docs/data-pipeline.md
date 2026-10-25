# Data pipeline

The implemented DAG sequence is:

```text
reload_raw -> dbt_build_core -> enrich_reviews -> dbt_build_ai
```

`reload_raw` issues seven `COPY INTO` statements against the configured Snowflake stage. Snowflake may report zero files when staged files have already been consumed.

`dbt_build_core` excludes models tagged `ai` and builds staging, dimensions, facts, and non-AI marts.

`enrich_reviews` reads unprocessed comments from `ZOMATO.RAW.REVIEWS`, classifies up to 100 rows, and inserts them into `ZOMATO.AI.REVIEW_ENRICHED`.

`dbt_build_ai` selects the `ai` tag and builds `mart_review_insights`.

No repository code uploads local CSV files to S3. Authorized users must provide source files through their own controlled ingestion process.
