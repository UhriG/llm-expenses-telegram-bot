import logging
from models.transaction import Transaction, ExchangeTransaction
from utils.logger import logger

# Note: In a further refactor you might move these enums to their own file.
# For now, we use string literals for transaction types and money types.

class TransactionProcessor:
    def __init__(self, transaction_service):
        self.transaction_service = transaction_service

    def process_transaction(self, user_id: int, group_id: int, transaction_data: dict) -> None:
        if transaction_data['type'] == "exchange":
            self._process_exchange_transaction(user_id, group_id, transaction_data)
        else:
            self._process_regular_transaction(user_id, group_id, transaction_data)

    def _process_exchange_transaction(self, user_id: int, group_id: int, data: dict) -> None:
        # Calculate exchange rate if not provided
        if 'exchange_rate' not in data:
            data['exchange_rate'] = data['target_amount'] / data['amount']

        transaction = Transaction(
            user_id=user_id,
            group_id=group_id,
            transaction_type="income",  # Using "income" for exchange transactions
            amount=data['target_amount'],
            description=self._format_exchange_description(data),
            category_id=self._get_category_id("exchange"),
            money_type_id=self._get_money_type_id(data.get('money_type', "cash"))
        )
        transaction_id = self.transaction_service.add_transaction(transaction)
        exchange_transaction = ExchangeTransaction(
            transaction_id=transaction_id,
            source_currency=data['source_currency'],
            target_currency=data['target_currency'],
            exchange_rate=data['exchange_rate']
        )
        self.transaction_service.add_exchange_transaction(exchange_transaction)

    def _process_regular_transaction(self, user_id: int, group_id: int, data: dict) -> None:
        is_expense = data['type'] == "expense"

        # Clean up description
        description = data.get('description', '').strip()
        if description:
            description = description[0].upper() + description[1:].lower()

        # Log if a new category should be created
        if data.get('should_create_category', False):
            category_name = data['category']
            category_reason = data.get('category_reason', 'New category needed')
            logger.info(f"Creating new category '{category_name}'. Reason: {category_reason}")

        category_id = self._get_category_id(data.get('category'))
        money_type_id = self._get_money_type_id(data.get('money_type', "cash"))
        transaction = Transaction(
            user_id=user_id,
            group_id=group_id,
            transaction_type=data['type'],
            amount=data['amount'] * (-1 if is_expense else 1),
            description=description,
            category_id=category_id,
            money_type_id=money_type_id
        )
        self.transaction_service.add_transaction(transaction)

        # Log the mappings for verification
        category_name = self.transaction_service.db.get_category_name(category_id)
        money_type_name = self.transaction_service.db.get_money_type_name(money_type_id)
        logger.info(f"Transaction saved with category: {category_id} ({category_name}), "
                    f"money_type: {money_type_id} ({money_type_name})")

    def _format_exchange_description(self, data: dict) -> str:
        return (
            f"Exchange: {data['amount']} {data['source_currency']} → "
            f"{data['target_amount']} {data['target_currency']}"
        )

    def _get_category_id(self, category_name: str) -> int:
        if not category_name:
            return self._get_category_id("otros")
        return self.transaction_service.db.get_or_create_category(category_name)

    def _get_money_type_id(self, money_type: str) -> int:
        if not money_type:
            return self._get_money_type_id("cash")
        return self.transaction_service.db.get_or_create_money_type(money_type) 