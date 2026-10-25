# Architecture

```mermaid
flowchart TD
    S3[AWS S3 stage paths] --> RAW[Snowflake ZOMATO.RAW]
    RAW --> STG[dbt staging views]
    STG --> CORE[dbt core marts]
    RAW --> SENT[Local RoBERTa task]
    SENT --> AI[ZOMATO.AI.REVIEW_ENRICHED]
    AI --> AIM[dbt mart_review_insights]
    CORE --> TSQL[Streamlit Text-to-SQL]
    STG --> RAG[Streamlit RAG]
    RAG --> OLLAMA[Ollama Qwen2.5]
    TSQL --> OLLAMA
    ORCH[Airflow zomato_batch] -. controls .-> RAW
    ORCH -. controls .-> CORE
    ORCH -. controls .-> SENT
    ORCH -. controls .-> AIM
```

Airflow is the control plane. Snowflake is the persistence and analytical execution layer. dbt owns SQL transformation logic. AI applications run locally and query Snowflake at runtime.

Schemas are `RAW` for source-aligned entities, `STAGING` for cleaned views, `MARTS` for analytical models, and `AI` for persisted review enrichment. The repository does not contain Snowflake DDL for stages, file formats, or schemas.
