from models.transaction import Transaction, ExchangeTransaction
from database import DatabaseHandler

class TransactionService:
    def __init__(self):
        self.db = DatabaseHandler()

    def add_transaction(self, transaction):
        transaction_id = self.db.add_transaction(
            transaction.user_id,
            transaction.group_id,
            transaction.type,
            transaction.amount,
            transaction.description,
            transaction.category_id,
            transaction.money_type_id
        )
        return transaction_id

    def add_exchange_transaction(self, exchange_transaction):
        self.db.add_exchange_transaction(
            exchange_transaction.transaction_id,
            exchange_transaction.source_currency,
            exchange_transaction.target_currency,
            exchange_transaction.exchange_rate
        ) 