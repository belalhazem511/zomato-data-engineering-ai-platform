# RAG assistant

`ai/rag_chat.py` loads up to 500 sampled reviews from `ZOMATO.STAGING.STG_REVIEWS`, removes empty comments, and embeds them with `sentence-transformers/all-MiniLM-L6-v2`.

Embeddings are normalized, so dot product is used as cosine similarity. The five highest-scoring reviews are placed into a constrained prompt and sent to local Ollama model `qwen2.5:3b`.

The application is evidence-limited: it retrieves from a sample, not the complete dataset, and is not intended for exact aggregate statistics. The UI displays the supporting reviews used for each answer.
