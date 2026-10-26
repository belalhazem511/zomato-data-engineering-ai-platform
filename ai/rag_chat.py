
import os
import numpy as np
import pandas as pd
import requests
import streamlit as st
import snowflake.connector

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

try:
    from .rag_core import (
        build_prompt,
        read_similarity_threshold,
        retrieve_reviews,
    )
except ImportError:
    from rag_core import (
        build_prompt,
        read_similarity_threshold,
        retrieve_reviews,
    )

load_dotenv()

# Configuration
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHAT_MODEL = "qwen2.5:1.5b"
OLLAMA_URL = "http://localhost:11434/api/generate"

NEW_REVIEWS = 500
TOP_K = 5
MIN_SIMILARITY = read_similarity_threshold(
    os.getenv("RAG_MIN_SIMILARITY")
)

st.set_page_config(
    page_title="Zomato AI Chat",
    page_icon="🍔",
    layout="wide"
)


@st.cache_resource
def load_embedding_model():
    return SentenceTransformer(
        EMBEDDING_MODEL,
        device="cpu"
    )


def get_connection():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "ZOMATO_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "ZOMATO"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "STAGING"),
        role=os.getenv("SNOWFLAKE_ROLE", "DBT_ROLE")
    )


def read_reviews_from_snowflake():
    conn = get_connection()

    try:
        query = f"""
            SELECT
                REVIEW_ID,
                CITY,
                RATING,
                COMMENT
            FROM ZOMATO.STAGING.STG_REVIEWS
            SAMPLE ({NEW_REVIEWS} ROWS)
        """

        df = conn.cursor().execute(
            query
        ).fetch_pandas_all()

        df.columns = [
            column.lower()
            for column in df.columns
        ]

        df = df.dropna(
            subset=["comment"]
        ).copy()

        df["comment"] = (
            df["comment"].astype(str)
        )

        df = df[
            df["comment"].str.strip() != ""
        ].reset_index(drop=True)

        return df

    finally:
        conn.close()


def embed(texts):
    model = load_embedding_model()

    embeddings = model.encode(
        texts,
        batch_size=32,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    return np.asarray(
        embeddings,
        dtype=np.float32
    )


@st.cache_data(ttl=3600, show_spinner=False)
def embed_question(question):
    return embed([question])[0]


# Cache reviews and embeddings for one hour.
# This replaces the old OpenAI embeddings cache.
@st.cache_data(ttl=3600, show_spinner="Loading review embeddings...")
def load_reviews():
    df = read_reviews_from_snowflake()

    if df.empty:
        return df, np.empty(
            (0, 384),
            dtype=np.float32
        )

    embeddings = embed(
        df["comment"].tolist()
    )

    return df, embeddings


def find_similar_reviews(question, df, embeddings):
    return retrieve_reviews(
        df,
        embeddings,
        embed_question(question),
        TOP_K,
        MIN_SIMILARITY,
    )


def ask_llm(question, top_reviews):
    prompt = build_prompt(question, top_reviews)

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": CHAT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 350
            }
        },
        timeout=300
    )

    response.raise_for_status()

    answer = response.json().get("response", "")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Ollama returned an empty or invalid response.")
    return answer.strip()


# ---------------- Streamlit UI ----------------

st.title("🍔 Zomato AI Review Assistant")

st.caption(
    f"Local RAG | MiniLM Embeddings | "
    f"{CHAT_MODEL} | No OpenAI API"
)

with st.spinner("Preparing reviews from Snowflake..."):
    try:
        review_df, review_embeddings = load_reviews()

    except Exception as error:
        st.error(
            f"Failed to load reviews: {error}"
        )
        st.stop()

if review_df.empty:
    st.warning("No usable reviews were found in Snowflake.")
    st.stop()

st.success(
    f"Loaded {len(review_df)} reviews successfully!"
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Reviews Loaded",
        len(review_df)
    )

with col2:
    st.metric(
        "Embedding Dimensions",
        review_embeddings.shape[1]
    )

with col3:
    st.metric(
        "Top Matches",
        TOP_K
    )

st.caption(
    f"Evidence threshold: cosine similarity ≥ {MIN_SIMILARITY:.2f}. "
    "Retrieved reviews are examples, not dataset-wide statistics."
)

st.divider()

question = st.text_input(
    "Ask a question about your reviews:",
    placeholder=(
        "What are the most common complaints "
        "about delivery?"
    )
)

if question.strip():
    with st.spinner("Searching relevant reviews..."):
        top_reviews = find_similar_reviews(
            question,
            review_df,
            review_embeddings
        )

    if top_reviews.empty:
        st.warning(
            "No reviews met the relevance threshold. "
            "Try a more specific question or lower RAG_MIN_SIMILARITY deliberately."
        )
        st.stop()

    with st.spinner("Generating local AI answer..."):
        try:
            answer = ask_llm(
                question,
                top_reviews
            )

            st.subheader("AI Answer")
            st.write(answer)

        except (requests.exceptions.RequestException, ValueError) as error:
            st.error(
                "Cannot connect to Ollama. "
                "Make sure Ollama is running and "
                f"model '{CHAT_MODEL}' is downloaded."
            )
            st.caption(str(error))

    with st.expander(
        "View reviews used to build this answer",
        expanded=False
    ):
        st.dataframe(
            top_reviews[
                [
                    "review_id",
                    "city",
                    "rating",
                    "comment",
                    "score"
                ]
            ],
            hide_index=True,
            use_container_width=True
        )
        st.caption(
            "Supporting review IDs: "
            + ", ".join(str(value) for value in top_reviews["review_id"])
        )

st.divider()
st.caption(
    "Answers are based on retrieved review samples, "
    "not necessarily the entire dataset."
)
