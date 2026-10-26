# Analytics dashboard

Run the read-only Streamlit dashboard with:

```powershell
streamlit run dashboard/app.py
```

The dashboard queries the existing `MARTS` relations and `mart_review_insights`. It requires the same Snowflake connection variables as the AI apps plus an explicit `SNOWFLAKE_READONLY_ROLE`. It does not create, update, or delete Snowflake objects or records.

The dashboard includes executive KPIs, revenue trends, city and restaurant performance, delivery SLA metrics, customer age-segment ordering patterns, and sentiment/topic review summaries. Raw data and fabricated KPIs are not used.
