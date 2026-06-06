import unittest

from app.db.session import check_db_connection, init_db


class DatabaseConnectionTest(unittest.TestCase):
    def test_database_initializes_and_accepts_connections(self):
        init_db()

        self.assertTrue(check_db_connection())


if __name__ == "__main__":
    unittest.main()
