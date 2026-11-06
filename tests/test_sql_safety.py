import unittest

from nl2traj.runtime import validate_readonly_sql


class SQLSafetyTests(unittest.TestCase):
    def test_allows_select_and_cte(self):
        self.assertTrue(validate_readonly_sql("SELECT * FROM trips;")[0])
        self.assertTrue(validate_readonly_sql("WITH x AS (SELECT 1) SELECT * FROM x;")[0])

    def test_rejects_writes_and_multiple_statements(self):
        self.assertFalse(validate_readonly_sql("DROP TABLE trips;")[0])
        self.assertFalse(validate_readonly_sql("WITH x AS (DELETE FROM trips RETURNING *) SELECT * FROM x;")[0])
        self.assertFalse(validate_readonly_sql("SELECT 1; DROP TABLE trips;")[0])

    def test_ignores_keywords_and_semicolons_inside_literals(self):
        allowed, _ = validate_readonly_sql("SELECT 'DROP; DELETE' AS text;")
        self.assertTrue(allowed)


if __name__ == "__main__":
    unittest.main()
