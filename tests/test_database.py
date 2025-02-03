import unittest
from database import DatabaseHandler

class TestDatabaseHandler(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseHandler(db_name=':memory:')

    def test_add_transaction(self):
        transaction_id = self.db.add_transaction(1, 1, 'expense', 100.0, 'Test transaction', 1, 1)
        self.assertIsNotNone(transaction_id)

    def test_get_or_create_category(self):
        category_id = self.db.get_or_create_category('Test Category')
        self.assertIsNotNone(category_id)

    def test_get_or_create_money_type(self):
        money_type_id = self.db.get_or_create_money_type('Test Money Type')
        self.assertIsNotNone(money_type_id)

if __name__ == '__main__':
    unittest.main() 