import sqlite3
from datetime import datetime

class DatabaseHandler:
    def __init__(self, db_name='expenses.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                category TEXT,
                money_type TEXT,
                source TEXT,
                source_currency TEXT,
                target_currency TEXT,
                exchange_rate REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def add_transaction(self, user_id, group_id, transaction_type, amount, description=None, category=None, money_type=None, source=None, source_currency=None, target_currency=None, exchange_rate=None):
        self.cursor.execute('''
            INSERT INTO transactions (user_id, group_id, type, amount, description, category, money_type, source, source_currency, target_currency, exchange_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, group_id, transaction_type, amount, description, category, money_type, source, source_currency, target_currency, exchange_rate))
        self.conn.commit()

    def get_balance(self, group_id):
        self.cursor.execute('''
            SELECT SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END)
            FROM transactions
            WHERE group_id = ?
        ''', (group_id,))
        return self.cursor.fetchone()[0] or 0

    def get_transactions(self, user_id):
        self.cursor.execute('''
            SELECT * FROM transactions
            WHERE user_id = ?
            ORDER BY timestamp DESC
        ''', (user_id,))
        return self.cursor.fetchall()

    def get_balance_by_category(self, group_id, category):
        self.cursor.execute('''
            SELECT SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END)
            FROM transactions
            WHERE group_id = ? AND category = ?
        ''', (group_id, category))
        return self.cursor.fetchone()[0] or 0

    def get_balance_by_money_type(self, group_id, money_type):
        self.cursor.execute('''
            SELECT SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END)
            FROM transactions
            WHERE group_id = ? AND (money_type = ? OR money_type = 'bank_transfer')
        ''', (group_id, money_type))
        return self.cursor.fetchone()[0] or 0

    def get_transactions_by_category(self, user_id, category):
        self.cursor.execute('''
            SELECT * FROM transactions
            WHERE user_id = ? AND category = ?
            ORDER BY timestamp DESC
        ''', (user_id, category))
        return self.cursor.fetchall()

    def clear_transactions(self, user_id):
        self.cursor.execute('''
            DELETE FROM transactions
            WHERE user_id = ?
        ''', (user_id,))
        self.conn.commit()

    def close(self):
        self.conn.close() 