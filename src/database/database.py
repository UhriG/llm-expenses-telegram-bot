import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple
from utils.logger import logger

class DatabaseHandler:
    def __init__(self, db_name='expenses.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create necessary database tables."""
        # Modify transactions table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                category_id INTEGER,
                money_type_id INTEGER,
                currency TEXT NOT NULL DEFAULT 'ARS',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(category_id) REFERENCES categories(id),
                FOREIGN KEY(money_type_id) REFERENCES money_types(id)
            )
        ''')
        # ... rest of existing code ...

    def get_latest_transactions(self, group_id: int, limit: Optional[int] = 10, category: Optional[str] = None) -> List[tuple]:
        """Get latest transactions with their IDs and descriptions."""
        # ... (keep existing implementation)

    def delete_transaction(self, transaction_id: int, group_id: int) -> bool:
        """Delete a specific transaction."""
        # ... (keep existing implementation)

    def rename_category(self, old_name: str, new_name: str) -> Tuple[bool, str]:
        """Rename a category."""
        # ... (keep existing implementation)

    def clear_transactions(self, group_id: int) -> None:
        """Clear all transactions and reset IDs."""
        try:
            # First delete all exchange transactions for the group
            self.cursor.execute('''
                DELETE FROM exchange_transactions
                WHERE transaction_id IN (
                    SELECT id FROM transactions WHERE group_id = ?
                )
            ''', (group_id,))
            
            # Then delete all transactions for the group
            self.cursor.execute('DELETE FROM transactions WHERE group_id = ?', (group_id,))
            
            # Reset the sequence for transaction IDs
            self.cursor.execute('DELETE FROM sqlite_sequence WHERE name = "transactions"')
            
            self.conn.commit()
            logger.info(f"Cleared all transactions and exchange transactions for group {group_id} and reset IDs")
        except Exception as e:
            logger.error(f"Error clearing transactions: {e}")
            self.conn.rollback()
            raise

    def add_exchange_transaction(self, exchange_transaction):
        """Add an exchange transaction to the database."""
        self.cursor.execute('''
            INSERT INTO exchange_transactions 
            (transaction_id, source_currency, target_currency, exchange_rate, source_amount, target_amount)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            exchange_transaction.transaction_id,
            exchange_transaction.source_currency,
            exchange_transaction.target_currency,
            exchange_transaction.exchange_rate,
            exchange_transaction.source_amount,
            exchange_transaction.target_amount
        ))
        self.conn.commit()

    def get_balance_by_money_type_and_currency(self, group_id: int, money_type_id: int, currency: str) -> float:
        """Get balance for a specific money type and currency."""
        self.cursor.execute('''
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE group_id = ? AND money_type_id = ? AND currency = ?
        ''', (group_id, money_type_id, currency))
        return self.cursor.fetchone()[0]

    # ... (keep all other existing database methods) 