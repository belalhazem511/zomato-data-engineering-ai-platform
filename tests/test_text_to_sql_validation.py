import os
import re
import unittest
from unittest.mock import patch

from ai.text_to_sql_validation import (
    TABLE_SCHEMAS,
    bounded_query,
    required_read_only_role,
    schema_prompt,
    validate_sql,
)


try:
    import sqlglot  # noqa: F401
except ImportError:
    SQLGLOT_AVAILABLE = False
else:
    SQLGLOT_AVAILABLE = True


class TextToSQLContractTests(unittest.TestCase):
    def test_schema_matches_known_dbt_names(self):
        self.assertIn("DIM_RESTAURANTS", TABLE_SCHEMAS)
        self.assertNotIn("DIM_RESTAURANT", TABLE_SCHEMAS)
        self.assertNotIn("city", TABLE_SCHEMAS["DIM_CUSTOMER"])
        self.assertEqual(TABLE_SCHEMAS["MART_DELIVERY_SLA"][-2:], ("p50", "p90"))
        self.assertIn("MART_DAILY_CITY_REVENUNE", schema_prompt())

    def test_prompt_does_not_advertise_removed_columns(self):
        prompt = schema_prompt()
        self.assertIsNone(re.search(r"DIM_RESTAURANT\(", prompt))
        self.assertNotIn("p50_delivery_min", prompt)
        self.assertNotIn("late_rate", prompt)

    def test_read_only_role_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SNOWFLAKE_READONLY_ROLE"):
                required_read_only_role()

    def test_read_only_role_is_explicit(self):
        with patch.dict(os.environ, {"SNOWFLAKE_READONLY_ROLE": "ANALYTICS_READONLY"}):
            self.assertEqual(required_read_only_role(), "ANALYTICS_READONLY")

    def test_bounded_query_is_positive_and_limited(self):
        self.assertEqual(
            bounded_query("SELECT city FROM MART_DAILY_CITY_REVENUNE", 100),
            "SELECT * FROM (SELECT city FROM MART_DAILY_CITY_REVENUNE) AS SAFE_RESULT LIMIT 100",
        )
        with self.assertRaises(ValueError):
            bounded_query("SELECT 1", 0)


@unittest.skipUnless(SQLGLOT_AVAILABLE, "SQLGlot is not installed in this environment")
class SQLGlotSafetyTests(unittest.TestCase):
    def test_valid_query_and_column_alias(self):
        sql = validate_sql(
            "SELECT city, SUM(gmv) AS total_gmv "
            "FROM MART_DAILY_CITY_REVENUNE "
            "GROUP BY city ORDER BY total_gmv DESC LIMIT 10"
        )
        self.assertIn("MART_DAILY_CITY_REVENUNE", sql)

    def test_rejects_unknown_column(self):
        with self.assertRaisesRegex(ValueError, "does not exist|not in the approved"):
            validate_sql("SELECT late_rate FROM MART_DELIVERY_SLA")

    def test_rejects_unauthorized_table(self):
        with self.assertRaisesRegex(ValueError, "not allowed"):
            validate_sql("SELECT * FROM RAW.REVIEWS")

    def test_rejects_writes_and_multiple_statements(self):
        with self.assertRaises(ValueError):
            validate_sql("DELETE FROM FCT_ORDERS")
        with self.assertRaisesRegex(ValueError, "one SQL statement"):
            validate_sql("SELECT * FROM FCT_ORDERS; SELECT * FROM DIM_DATE")


if __name__ == "__main__":
    unittest.main()
