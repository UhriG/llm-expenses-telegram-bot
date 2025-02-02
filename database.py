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
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def add_transaction(self, user_id, transaction_type, amount, description=None):
        self.cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, description)
            VALUES (?, ?, ?, ?)
        ''', (user_id, transaction_type, amount, description))
        self.conn.commit()

    def get_balance(self, user_id):
        self.cursor.execute('''
            SELECT SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END)
            FROM transactions
            WHERE user_id = ?
        ''', (user_id,))
        return self.cursor.fetchone()[0] or 0

    def get_transactions(self, user_id):
        self.cursor.execute('''
            SELECT * FROM transactions
            WHERE user_id = ?
            ORDER BY timestamp DESC
        ''', (user_id,))
        return self.cursor.fetchall()

    def close(self):
        self.conn.close() 