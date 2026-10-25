"""Pure, testable complaint and topic rules used by review enrichment."""

from __future__ import annotations

import re


TOPIC_KEYWORDS = {
    "food quality": [
        "food", "taste", "tasty", "tasteless", "delicious", "cold food",
        "fresh", "stale", "meal", "flavor", "quality", "spoiled",
        "undercooked", "overcooked",
    ],
    "delivery": [
        "delivery", "delivered", "late", "driver", "courier", "arrived",
        "delay", "delayed", "slow delivery", "long wait",
    ],
    "pricing": [
        "price", "pricing", "expensive", "cost", "cheap", "overpriced",
        "money", "value", "pricey",
    ],
    "service": [
        "service", "staff", "support", "rude", "polite", "helpful",
        "customer service", "unhelpful",
    ],
    "packaging": [
        "packaging", "package", "packed", "container", "box", "spilled",
        "leaking", "broken container",
    ],
}

ISSUE_RULES = [
    (
        ["late", "delay", "delayed", "took too long", "long wait", "slow delivery", "arrived late"],
        "Delayed delivery",
        "delivery",
    ),
    (
        ["cold food", "food was cold", "arrived cold", "not hot", "cold meal"],
        "Food arrived cold",
        "food quality",
    ),
    (
        ["stale", "not fresh", "spoiled", "undercooked", "overcooked", "bad taste", "tasteless"],
        "Food quality issue",
        "food quality",
    ),
    (
        ["expensive", "overpriced", "too pricey", "high price", "not worth the money"],
        "High price",
        "pricing",
    ),
    (
        ["rude", "unhelpful", "bad service", "poor service", "unprofessional"],
        "Poor customer service",
        "service",
    ),
    (
        ["spilled", "leaking", "damaged packaging", "broken container", "poor packaging"],
        "Packaging issue",
        "packaging",
    ),
]

NEGATION_PATTERN = re.compile(
    r"\b(?:not|never|no|without|isn't|wasn't|didn't|don't|hardly)"
    r"(?:\s+\w+){0,2}\s*$"
)


def contains_phrase(text: str, phrase: str) -> bool:
    pattern = (
        r"\b"
        + r"\s+".join(re.escape(word) for word in phrase.split())
        + r"\b"
    )
    for match in re.finditer(pattern, text):
        prefix = text[:match.start()]
        if not NEGATION_PATTERN.search(prefix):
            return True
    return False


def detect_issues(comment, sentiment):
    """Return every distinct matching complaint for optional multi-label use."""

    if sentiment != "negative":
        return []

    text = str(comment).lower()
    matches = []
    for rule_index, (keywords, issue, topic) in enumerate(ISSUE_RULES):
        matched_phrases = [
            keyword for keyword in keywords if contains_phrase(text, keyword)
        ]
        if matched_phrases:
            matches.append(
                {
                    "issue": issue,
                    "topic": topic,
                    "matched_phrases": tuple(matched_phrases),
                    "specificity": max(len(phrase.split()) for phrase in matched_phrases),
                    "rule_index": rule_index,
                }
            )

    matches.sort(key=lambda item: (-item["specificity"], item["rule_index"]))
    return matches


def detect_issue(comment, sentiment):
    """Return the legacy single best issue and topic."""

    matches = detect_issues(comment, sentiment)
    if not matches:
        return None, None
    best = matches[0]
    return best["issue"], best["topic"]


def find_topic(comment):
    text = str(comment).lower()
    scores = {
        topic: sum(contains_phrase(text, keyword) for keyword in keywords)
        for topic, keywords in TOPIC_KEYWORDS.items()
    }
    best_topic = max(scores, key=scores.get)
    return best_topic if scores[best_topic] else "other"


def analyze_topic_and_issue(comment, sentiment):
    issue, issue_topic = detect_issue(comment, sentiment)
    if issue is not None:
        return issue_topic, issue
    return find_topic(comment), None
