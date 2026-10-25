
import argparse
import os
import re

import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
SAMPLE_N = 100

TOPIC_KEYWORDS = {
    "food quality": [
        "food", "taste", "tasty", "tasteless",
        "delicious", "cold food", "fresh",
        "stale", "meal", "flavor", "quality",
        "spoiled", "undercooked", "overcooked"
    ],
    "delivery": [
        "delivery", "delivered", "late",
        "driver", "courier", "arrived",
        "delay", "delayed", "slow delivery",
        "long wait"
    ],
    "pricing": [
        "price", "pricing", "expensive",
        "cost", "cheap", "overpriced",
        "money", "value", "pricey"
    ],
    "service": [
        "service", "staff", "support",
        "rude", "polite", "helpful",
        "customer service", "unhelpful"
    ],
    "packaging": [
        "packaging", "package", "packed",
        "container", "box", "spilled",
        "leaking", "broken container"
    ]
}

ISSUE_RULES = [
    (
        [
            "late", "delay", "delayed",
            "took too long", "long wait",
            "slow delivery", "arrived late"
        ],
        "Delayed delivery",
        "delivery"
    ),
    (
        [
            "cold food", "food was cold",
            "arrived cold", "not hot",
            "cold meal"
        ],
        "Food arrived cold",
        "food quality"
    ),
    (
        [
            "stale", "not fresh", "spoiled",
            "undercooked", "overcooked",
            "bad taste", "tasteless"
        ],
        "Food quality issue",
        "food quality"
    ),
    (
        [
            "expensive", "overpriced",
            "too pricey", "high price",
            "not worth the money"
        ],
        "High price",
        "pricing"
    ),
    (
        [
            "rude", "unhelpful",
            "bad service", "poor service",
            "unprofessional"
        ],
        "Poor customer service",
        "service"
    ),
    (
        [
            "spilled", "leaking",
            "damaged packaging",
            "broken container",
            "poor packaging"
        ],
        "Packaging issue",
        "packaging"
    )
]


def contains_phrase(text, phrase):
    pattern = (
        r"\b"
        + r"\s+".join(
            re.escape(word)
            for word in phrase.split()
        )
        + r"\b"
    )

    return bool(re.search(pattern, text))


def detect_issue(comment, sentiment):
    if sentiment != "negative":
        return None, None

    text = str(comment).lower()

    matches = []

    for keywords, issue, topic in ISSUE_RULES:
        matched_phrases = [
            keyword
            for keyword in keywords
            if contains_phrase(text, keyword)
        ]

        if matched_phrases:
            matches.append((
                max(
                    len(phrase.split())
                    for phrase in matched_phrases
                ),
                issue,
                topic
            ))

    if not matches:
        return None, None

    # Prefer the most specific matching phrase.
    matches.sort(
        key=lambda item: item[0],
        reverse=True
    )

    _, issue, topic = matches[0]

    return issue, topic


def find_topic(comment):
    text = str(comment).lower()
    scores = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        scores[topic] = sum(
            1
            for keyword in keywords
            if contains_phrase(text, keyword)
        )

    best_topic = max(
        scores,
        key=scores.get
    )

    if scores[best_topic] == 0:
        return "other"

    return best_topic


def analyze_topic_and_issue(comment, sentiment):
    issue, issue_topic = detect_issue(
        comment,
        sentiment
    )

    # When a negative review has a clear issue,
    # keep topic and issue consistent.
    if issue is not None:
        return issue_topic, issue

    return find_topic(comment), None


def find_key_issue(comment, sentiment):
    _, issue = analyze_topic_and_issue(
        comment,
        sentiment
    )
    return issue


def get_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv(
            "SNOWFLAKE_WAREHOUSE",
            "ZOMATO_WH"
        ),
        database=os.getenv(
            "SNOWFLAKE_DATABASE",
            "ZOMATO"
        ),
        schema="AI",
        role=os.getenv(
            "SNOWFLAKE_ROLE",
            "DBT_ROLE"
        )
    )


def create_output_table(cursor):
    cursor.execute(
        "CREATE SCHEMA IF NOT EXISTS ZOMATO.AI"
    )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS
        ZOMATO.AI.REVIEW_ENRICHED (
            REVIEW_ID STRING,
            SENTIMENT_LABEL STRING,
            SENTIMENT_SCORE FLOAT,
            TOPIC STRING,
            KEY_ISSUE STRING,
            MODEL STRING,
            ENRICHED_AT TIMESTAMP_LTZ
        )
    """)

    cursor.execute("""
        ALTER TABLE ZOMATO.AI.REVIEW_ENRICHED
        ADD COLUMN IF NOT EXISTS
        ENRICHED_AT TIMESTAMP_LTZ
    """)


def get_reviews_to_enrich(cursor):
    cursor.execute("""
        SELECT r.REVIEW_ID, r.COMMENT
        FROM ZOMATO.RAW.REVIEWS r
        WHERE r.COMMENT IS NOT NULL
          AND TRIM(r.COMMENT) <> ''
          AND NOT EXISTS (
              SELECT 1
              FROM ZOMATO.AI.REVIEW_ENRICHED e
              WHERE e.REVIEW_ID = r.REVIEW_ID
          )
        ORDER BY r.REVIEW_ID
        LIMIT %s
    """, (SAMPLE_N,))

    return cursor.fetchall()


def load_model():
    from transformers import pipeline

    print(
        "Loading local RoBERTa model...",
        flush=True
    )

    classifier = pipeline(
        "text-classification",
        model=MODEL,
        device=-1
    )

    print(
        "AI model loaded successfully!",
        flush=True
    )

    return classifier


def classify_review(comment, classifier):
    predictions = classifier(
        str(comment),
        truncation=True,
        top_k=None
    )

    probabilities = {
        item["label"].lower(): item["score"]
        for item in predictions
    }

    sentiment = max(
        probabilities,
        key=probabilities.get
    )

    sentiment_score = (
        probabilities.get("positive", 0.0)
        - probabilities.get("negative", 0.0)
    )

    topic, key_issue = analyze_topic_and_issue(
        comment,
        sentiment
    )

    return {
        "sentiment_label": sentiment,
        "sentiment_score": round(
            sentiment_score, 4
        ),
        "topic": topic,
        "key_issue": key_issue
    }


def save_results(cursor, results):
    if not results:
        return

    cursor.executemany("""
        INSERT INTO ZOMATO.AI.REVIEW_ENRICHED (
            REVIEW_ID,
            SENTIMENT_LABEL,
            SENTIMENT_SCORE,
            TOPIC,
            KEY_ISSUE,
            MODEL,
            ENRICHED_AT
        )
        VALUES (
            %s, %s, %s, %s, %s, %s,
            CURRENT_TIMESTAMP()
        )
    """, results)


def enrich_new_reviews():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        create_output_table(cursor)

        reviews = get_reviews_to_enrich(cursor)

        if not reviews:
            print(
                "No new reviews to enrich.",
                flush=True
            )
            return

        classifier = load_model()

        print(
            f"Enriching {len(reviews)} reviews...",
            flush=True
        )

        results = []
        failures = 0

        for review_id, comment in reviews:
            try:
                result = classify_review(
                    comment,
                    classifier
                )

                print(
                    f"Review {review_id}: "
                    f"{result['sentiment_label']} | "
                    f"{result['sentiment_score']} | "
                    f"{result['topic']} | "
                    f"{result['key_issue']}",
                    flush=True
                )

                results.append((
                    str(review_id),
                    result["sentiment_label"],
                    result["sentiment_score"],
                    result["topic"],
                    result["key_issue"],
                    MODEL
                ))

            except Exception as error:
                failures += 1
                print(
                    f"Failed review {review_id}: "
                    f"{error}",
                    flush=True
                )

        if failures:
            conn.rollback()
            raise RuntimeError(
                f"{failures} reviews failed. "
                "No results were saved."
            )

        save_results(cursor, results)
        conn.commit()

        print(
            f"Saved {len(results)} enriched "
            "reviews to Snowflake.",
            flush=True
        )

    except Exception:
        if conn is not None:
            conn.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None:
            conn.close()


def test_issue_detection():
    examples = [
        (
            "The delivery arrived very late",
            "negative",
            "delivery",
            "Delayed delivery"
        ),
        (
            "The food was cold and tasteless",
            "negative",
            "food quality",
            "Food arrived cold"
        ),
        (
            "The meal was overpriced",
            "negative",
            "pricing",
            "High price"
        ),
        (
            "The staff were rude",
            "negative",
            "service",
            "Poor customer service"
        ),
        (
            "The packaging was leaking",
            "negative",
            "packaging",
            "Packaging issue"
        ),
        (
            "The food was delicious",
            "positive",
            "food quality",
            None
        )
    ]

    passed = 0

    for comment, sentiment, expected_topic, expected_issue in examples:
        topic, issue = analyze_topic_and_issue(
            comment,
            sentiment
        )

        success = (
            topic == expected_topic
            and issue == expected_issue
        )

        if success:
            passed += 1

        print(
            f"{'PASS' if success else 'FAIL'} | "
            f"{comment}\n"
            f"  Topic: {topic}\n"
            f"  Issue: {issue}\n"
        )

    print(
        f"Tests passed: {passed}/{len(examples)}"
    )

    if passed != len(examples):
        raise AssertionError(
            "Some issue detection tests failed."
        )


def preview_existing_reviews():
    conn = get_connection()
    cursor = None

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                e.REVIEW_ID,
                r.COMMENT,
                e.SENTIMENT_LABEL,
                e.TOPIC,
                e.KEY_ISSUE
            FROM ZOMATO.AI.REVIEW_ENRICHED e
            JOIN ZOMATO.RAW.REVIEWS r
              ON e.REVIEW_ID = r.REVIEW_ID
            WHERE r.COMMENT IS NOT NULL
            ORDER BY e.REVIEW_ID
            LIMIT 20
        """)

        changes = 0

        for review_id, comment, sentiment, old_topic, old_issue in cursor:
            new_topic, new_issue = analyze_topic_and_issue(
                comment,
                sentiment
            )

            changed = (
                new_topic != old_topic
                or new_issue != old_issue
            )

            if changed:
                changes += 1

            print(
                f"Review {review_id}\n"
                f"  Old: {old_topic} | {old_issue}\n"
                f"  New: {new_topic} | {new_issue}\n"
                f"  Changed: {changed}\n"
            )

        print(
            f"Changed in preview: {changes}"
        )

    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def update_existing_reviews():
    conn = get_connection()
    cursor = None

    try:
        cursor = conn.cursor()

        # Backup before changes.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS
            ZOMATO.AI.REVIEW_ENRICHED_BACKUP
            CLONE ZOMATO.AI.REVIEW_ENRICHED
        """)

        cursor.execute("""
            SELECT
                e.REVIEW_ID,
                r.COMMENT,
                e.SENTIMENT_LABEL,
                e.TOPIC,
                e.KEY_ISSUE
            FROM ZOMATO.AI.REVIEW_ENRICHED e
            JOIN ZOMATO.RAW.REVIEWS r
              ON e.REVIEW_ID = r.REVIEW_ID
            WHERE r.COMMENT IS NOT NULL
        """)

        rows = cursor.fetchall()
        updates = []

        for review_id, comment, sentiment, old_topic, old_issue in rows:
            new_topic, new_issue = analyze_topic_and_issue(
                comment,
                sentiment
            )

            if (
                new_topic != old_topic
                or new_issue != old_issue
            ):
                updates.append((
                    new_topic,
                    new_issue,
                    str(review_id)
                ))

        for topic, issue, review_id in updates:
            cursor.execute("""
                UPDATE ZOMATO.AI.REVIEW_ENRICHED
                SET TOPIC = %s,
                    KEY_ISSUE = %s
                WHERE REVIEW_ID = %s
            """, (topic, issue, review_id))

        conn.commit()

        print(
            f"Updated {len(updates)} existing reviews."
        )
        print(
            "Backup: "
            "ZOMATO.AI.REVIEW_ENRICHED_BACKUP"
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--test",
        action="store_true",
        help="Test issue detection locally"
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview changes without writing"
    )

    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing topics and issues"
    )

    args = parser.parse_args()

    if args.test:
        test_issue_detection()

    elif args.preview:
        preview_existing_reviews()

    elif args.update_existing:
        update_existing_reviews()

    else:
        enrich_new_reviews()


if __name__ == "__main__":
    main()
