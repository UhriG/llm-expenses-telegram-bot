import unittest
from services.transaction_service import TransactionService
from models.transaction import Transaction, ExchangeTransaction

class TestTransactionService(unittest.TestCase):
    def setUp(self):
        self.service = TransactionService()

    def test_add_transaction(self):
        transaction = Transaction(1, 1, 'expense', 100.0, 'Test transaction', 1, 1)
        transaction_id = self.service.add_transaction(transaction)
        self.assertIsNotNone(transaction_id)

    def test_add_exchange_transaction(self):
        exchange_transaction = ExchangeTransaction(1, 'USD', 'ARS', 100.0)
        self.service.add_exchange_transaction(exchange_transaction)

if __name__ == '__main__':
    unittest.main() 