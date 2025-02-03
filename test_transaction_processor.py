import unittest
from services.dummy_transaction_service import DummyTransactionService
from processors.transaction_processor import TransactionProcessor

class DummyDB:
    def __init__(self):
        self.categories = ['comida', 'otros']
    def get_or_create_category(self, category_name):
        return 1
    def get_or_create_money_type(self, money_type):
        return 1

class DummyTransactionService:
    def __init__(self):
        self.db = DummyDB()
    def add_transaction(self, transaction):
        return 42  # dummy transaction id
    def add_exchange_transaction(self, exchange_transaction):
        pass

class TestTransactionProcessor(unittest.TestCase):
    def setUp(self):
        self.transaction_service = DummyTransactionService()
        self.processor = TransactionProcessor(self.transaction_service)

    def test_process_exchange_transaction_calculates_rate(self):
        data = {
            "type": "exchange",
            "amount": 100.0,
            "target_amount": 90000.0,
            "source_currency": "USD",
            "target_currency": "ARS",
            "money_type": "cash"
        }
        # This should set the exchange_rate internally if not provided.
        self.processor._process_exchange_transaction(1, 1, data)
        self.assertAlmostEqual(data['exchange_rate'], 900.0)

if __name__ == '__main__':
    unittest.main() 