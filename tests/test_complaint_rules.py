import unittest

from ai.complaint_rules import analyze_topic_and_issue, detect_issues


class ComplaintRuleTests(unittest.TestCase):
    def test_legacy_best_issue_is_preserved(self):
        self.assertEqual(
            analyze_topic_and_issue("The delivery arrived very late", "negative"),
            ("delivery", "Delayed delivery"),
        )
        self.assertEqual(
            analyze_topic_and_issue("The food was cold and tasteless", "negative"),
            ("food quality", "Food arrived cold"),
        )
        self.assertEqual(
            analyze_topic_and_issue("The meal was overpriced", "negative"),
            ("pricing", "High price"),
        )

    def test_multiple_complaints_are_available_without_changing_legacy_output(self):
        issues = detect_issues("The food was stale and overpriced", "negative")
        self.assertEqual(
            [(item["topic"], item["issue"]) for item in issues],
            [("food quality", "Food quality issue"), ("pricing", "High price")],
        )
        self.assertEqual(
            analyze_topic_and_issue("The food was stale and overpriced", "negative"),
            ("food quality", "Food quality issue"),
        )

    def test_multiple_operational_complaints_are_detected(self):
        issues = detect_issues(
            "The delivery was late and the packaging was leaking",
            "negative",
        )
        self.assertEqual(
            {item["issue"] for item in issues},
            {"Delayed delivery", "Packaging issue"},
        )

    def test_negated_wording_does_not_create_a_complaint(self):
        self.assertEqual(
            detect_issues("The food was not stale and the service was not rude", "negative"),
            [],
        )

    def test_neutral_and_positive_reviews_have_no_complaint(self):
        self.assertEqual(detect_issues("The food was stale", "neutral"), [])
        self.assertEqual(detect_issues("The food was delicious", "positive"), [])

    def test_ambiguous_negative_review_has_no_forced_issue(self):
        self.assertEqual(
            analyze_topic_and_issue("The experience was disappointing", "negative"),
            ("other", None),
        )


if __name__ == "__main__":
    unittest.main()
