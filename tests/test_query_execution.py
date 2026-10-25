import unittest
from unittest.mock import Mock

from ai.query_execution import execute_dataframe


class QueryExecutionTests(unittest.TestCase):
    def test_executes_bounded_query_and_closes_resources(self):
        connection = Mock()
        cursor = connection.cursor.return_value
        expected = object()
        cursor.fetch_pandas_all.return_value = expected

        result = execute_dataframe(
            connection,
            "SELECT city FROM MART_DAILY_CITY_REVENUNE",
            100,
        )

        self.assertIs(result, expected)
        cursor.execute.assert_called_once_with(
            "SELECT * FROM (SELECT city FROM MART_DAILY_CITY_REVENUNE) AS SAFE_RESULT LIMIT 100"
        )
        cursor.close.assert_called_once_with()
        connection.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
