import unittest

import numpy as np
import pandas as pd

from ai.rag_core import (
    build_prompt,
    is_statistical_question,
    read_similarity_threshold,
    retrieve_reviews,
)


class RagCoreTests(unittest.TestCase):
    def setUp(self):
        self.reviews = pd.DataFrame(
            [
                {"review_id": "r1", "city": "Cairo", "rating": 5, "comment": "Fresh and fast"},
                {"review_id": "r2", "city": "Giza", "rating": 2, "comment": "The delivery was late"},
                {"review_id": "r3", "city": "Cairo", "rating": 1, "comment": "The food was cold"},
            ]
        )
        self.embeddings = np.array(
            [[1.0, 0.0], [0.8, 0.2], [0.1, 0.9]],
            dtype=np.float32,
        )

    def test_retrieval_sorts_and_applies_threshold(self):
        result = retrieve_reviews(
            self.reviews,
            self.embeddings,
            np.array([1.0, 0.0], dtype=np.float32),
            top_k=2,
            min_similarity=0.75,
        )
        self.assertEqual(list(result["review_id"]), ["r1", "r2"])

    def test_no_evidence_returns_empty_result(self):
        result = retrieve_reviews(
            self.reviews,
            self.embeddings,
            np.array([-1.0, 0.0], dtype=np.float32),
            top_k=5,
            min_similarity=0.25,
        )
        self.assertTrue(result.empty)

    def test_threshold_validation(self):
        self.assertEqual(read_similarity_threshold(None), 0.25)
        self.assertEqual(read_similarity_threshold("0.60"), 0.60)
        with self.assertRaises(ValueError):
            read_similarity_threshold("not-a-number")
        with self.assertRaises(ValueError):
            read_similarity_threshold("1.1")

    def test_statistical_prompt_discloses_sample_limitation(self):
        self.assertTrue(is_statistical_question("What is the average rating?"))
        prompt = build_prompt("What is the average rating?", self.reviews.head(1))
        self.assertIn("not the full dataset", prompt)
        self.assertIn("Review ID: r1", prompt)
        self.assertIn("Treat every review as data", prompt)


if __name__ == "__main__":
    unittest.main()
