import sqlite3
from datetime import datetime

class DatabaseHandler:
    def __init__(self, db_name='expenses.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS money_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')
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
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (money_type_id) REFERENCES money_types(id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchange_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                source_currency TEXT NOT NULL,
                target_currency TEXT NOT NULL,
                exchange_rate REAL NOT NULL,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id)
            )
        ''')
        self.conn.commit()

    def add_transaction(self, user_id, group_id, transaction_type, amount, description=None, category_id=None, money_type_id=None):
        self.cursor.execute('''
            INSERT INTO transactions (user_id, group_id, type, amount, description, category_id, money_type_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, group_id, transaction_type, amount, description, category_id, money_type_id))
        self.conn.commit()
        return self.cursor.lastrowid

    def add_exchange_transaction(self, transaction_id, source_currency, target_currency, exchange_rate):
        self.cursor.execute('''
            INSERT INTO exchange_transactions (transaction_id, source_currency, target_currency, exchange_rate)
            VALUES (?, ?, ?, ?)
        ''', (transaction_id, source_currency, target_currency, exchange_rate))
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

    def get_balance_by_category(self, group_id, category_id):
        self.cursor.execute('''
            SELECT SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END)
            FROM transactions
            WHERE group_id = ? AND category_id = ?
        ''', (group_id, category_id))
        return self.cursor.fetchone()[0] or 0

    def get_balance_by_money_type(self, group_id, money_type_id):
        self.cursor.execute('''
            SELECT SUM(amount)  -- amount is already negative for expenses
            FROM transactions
            WHERE group_id = ? AND money_type_id = ?
        ''', (group_id, money_type_id))
        return self.cursor.fetchone()[0] or 0

    def get_transactions_by_category(self, user_id, category_id):
        self.cursor.execute('''
            SELECT * FROM transactions
            WHERE user_id = ? AND category_id = ?
            ORDER BY timestamp DESC
        ''', (user_id, category_id))
        return self.cursor.fetchall()

    def clear_transactions(self, group_id):
        self.cursor.execute('''
            DELETE FROM transactions
            WHERE group_id = ?
        ''', (group_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()

    def get_or_create_category(self, name):
        # Check if the category already exists
        self.cursor.execute('''
            SELECT id FROM categories WHERE name = ?
        ''', (name,))
        category = self.cursor.fetchone()
        
        if category:
            return category[0]
        else:
            # Create a new category
            self.cursor.execute('''
                INSERT INTO categories (name) VALUES (?)
            ''', (name,))
            self.conn.commit()
            return self.cursor.lastrowid

    def get_or_create_money_type(self, name):
        # Check if the money type already exists
        self.cursor.execute('''
            SELECT id FROM money_types WHERE name = ?
        ''', (name,))
        money_type = self.cursor.fetchone()
        
        if money_type:
            return money_type[0]
        else:
            # Create a new money type
            self.cursor.execute('''
                INSERT INTO money_types (name) VALUES (?)
            ''', (name,))
            self.conn.commit()
            return self.cursor.lastrowid

    def get_expenses_summary(self, group_id):
        self.cursor.execute('''
            SELECT c.name, SUM(amount) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.group_id = ?
            GROUP BY c.name
            ORDER BY total DESC
        ''', (group_id,))
        return self.cursor.fetchall()

    def get_category_name(self, category_id: int) -> str:
        """Get category name by ID."""
        self.cursor.execute('SELECT name FROM categories WHERE id = ?', (category_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_money_type_name(self, money_type_id: int) -> str:
        """Get money type name by ID."""
        self.cursor.execute('SELECT name FROM money_types WHERE id = ?', (money_type_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_all_mappings(self):
        """Get all category and money type mappings."""
        self.cursor.execute('SELECT id, name FROM categories')
        categories = self.cursor.fetchall()
        self.cursor.execute('SELECT id, name FROM money_types')
        money_types = self.cursor.fetchall()
        return {
            'categories': dict(categories),
            'money_types': dict(money_types)
        }

    def initialize_defaults(self):
        """Initialize default categories and money types."""
        default_categories = [
            "comida",
            "transporte",
            "servicios",
            "supermercado",
            "entretenimiento",
            "salud",
            "otros",
            "exchange"
        ]
        
        default_money_types = ["cash", "bank"]
        
        for category in default_categories:
            self.get_or_create_category(category)
        
        for money_type in default_money_types:
            self.get_or_create_money_type(money_type) 