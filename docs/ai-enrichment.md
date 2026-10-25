# AI enrichment

`ai/enrich_reviews.py` uses `cardiffnlp/twitter-roberta-base-sentiment-latest` through Hugging Face Transformers on CPU.

For each previously unenriched review it stores review ID, sentiment label, sentiment score, topic, one key issue, model identifier, and enrichment timestamp.

Topics and issues are assigned with phrase-aware keyword rules. Issue detection runs only for negative sentiment and chooses one most-specific matching issue. This is intentionally not a multi-label classifier.

The rule engine now also exposes an optional `detect_all_issues()` path that returns every distinct matching issue with topic and matched phrases. The Airflow persistence path continues to use the legacy single `TOPIC` and `KEY_ISSUE` fields; no new table or historical update is performed automatically.

Phrase matching recognizes common negated wording such as “not stale” and “not rude” to avoid creating a complaint from a negation. The isolated regression suite covers legacy labels, multiple complaints, neutral/positive reviews, negation, and ambiguous wording.

The script also contains local tests, a read-only preview mode, and an optional historical update mode. The Airflow DAG invokes only the default new-review enrichment path.
