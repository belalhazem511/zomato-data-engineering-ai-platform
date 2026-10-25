import unittest

from dashboard.query_contract import (
    CUSTOMER_QUERY,
    DELIVERY_QUERY,
    EXECUTIVE_QUERY,
    MART_TABLES,
    REVENUE_BY_CITY_QUERY,
    REVIEW_QUERY,
    TOP_RESTAURANTS_QUERY,
    build_order_filters,
)


class DashboardContractTests(unittest.TestCase):
    def test_queries_use_existing_relations(self):
        for table in MART_TABLES:
            self.assertRegex(
                " ".join(
                    [
                        EXECUTIVE_QUERY,
                        REVENUE_BY_CITY_QUERY,
                        TOP_RESTAURANTS_QUERY,
                        DELIVERY_QUERY,
                        CUSTOMER_QUERY,
                        REVIEW_QUERY,
                    ]
                ),
                table,
            )

    def test_delivery_columns_match_current_mart(self):
        self.assertIn("p50", DELIVERY_QUERY)
        self.assertIn("p90", DELIVERY_QUERY)
        self.assertNotIn("p50_delivery_min", DELIVERY_QUERY)
        self.assertNotIn("late_rate", DELIVERY_QUERY)

    def test_filter_builder_is_parameterized(self):
        where, params = build_order_filters("Cairo", "2025-01-01", "2025-01-31")
        self.assertEqual(
            where,
            " WHERE city = %s AND order_date >= %s AND order_date <= %s",
        )
        self.assertEqual(params, ("Cairo", "2025-01-01", "2025-01-31"))
        self.assertEqual(build_order_filters(), ("", ()))


if __name__ == "__main__":
    unittest.main()
