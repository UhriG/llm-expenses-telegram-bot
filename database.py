import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple
from utils.logger import logger

class DatabaseHandler:
    def __init__(self, db_name='expenses.db'):
        self.conn = sqlite3.connect(db_name, timeout=20)
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
                currency TEXT NOT NULL DEFAULT 'ARS',
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
                source_amount REAL NOT NULL,
                target_amount REAL NOT NULL,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id)
            )
        ''')
        self.conn.commit()

    def add_transaction(self, user_id, group_id, transaction_type, amount, description=None, category_id=None, money_type_id=None, currency='ARS'):
        self.cursor.execute('''
            INSERT INTO transactions (
                user_id, group_id, type, amount, description, 
                category_id, money_type_id, currency
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, group_id, transaction_type, amount, description, 
            category_id, money_type_id, currency
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def add_exchange_transaction(self, transaction_id, source_currency, target_currency, exchange_rate, source_amount, target_amount):
        try:
            self.cursor.execute('BEGIN TRANSACTION')
            
            self.cursor.execute('''
                INSERT INTO exchange_transactions (
                    transaction_id, source_currency, target_currency, 
                    exchange_rate, source_amount, target_amount
                )
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                transaction_id, source_currency, target_currency, 
                exchange_rate, source_amount, target_amount
            ))
            
            self.cursor.execute('COMMIT')
            logger.info(f"Added exchange transaction record: {source_amount} {source_currency} → {target_amount} {target_currency}")
        except Exception as e:
            self.cursor.execute('ROLLBACK')
            logger.error(f"Error adding exchange transaction: {e}")
            raise

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

    def clear_transactions(self, group_id: int) -> None:
        """Clear all transactions and reset IDs."""
        try:
            # Start a transaction
            self.cursor.execute('BEGIN TRANSACTION')
            
            # Get all transaction IDs for this group
            self.cursor.execute('''
                SELECT id FROM transactions WHERE group_id = ?
            ''', (group_id,))
            transaction_ids = [row[0] for row in self.cursor.fetchall()]
            
            if transaction_ids:
                # Delete exchange transactions using IN clause
                self.cursor.execute('''
                    DELETE FROM exchange_transactions 
                    WHERE transaction_id IN ({})
                '''.format(','.join('?' * len(transaction_ids))), transaction_ids)
            
            # Delete transactions
            self.cursor.execute('DELETE FROM transactions WHERE group_id = ?', (group_id,))
            
            # Reset sequences
            self.cursor.execute('UPDATE sqlite_sequence SET seq = 0 WHERE name = "transactions"')
            self.cursor.execute('UPDATE sqlite_sequence SET seq = 0 WHERE name = "exchange_transactions"')
            
            # Commit transaction
            self.cursor.execute('COMMIT')
            logger.info(f"Cleared {len(transaction_ids)} transactions and their exchange records for group {group_id}")
            
        except Exception as e:
            self.cursor.execute('ROLLBACK')
            logger.error(f"Error clearing transactions: {e}")
            raise

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

    def get_all_categories(self):
        """Get all existing categories."""
        self.cursor.execute('SELECT name FROM categories')
        return [row[0] for row in self.cursor.fetchall()]

    def get_latest_transactions(self, group_id: int, limit: Optional[int] = 10, category: Optional[str] = None) -> List[tuple]:
        """Get latest transactions with their IDs and descriptions."""
        query = '''
            SELECT t.id, t.type, t.amount, t.description, c.name as category, t.timestamp
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.group_id = ?
        '''
        params = [group_id]
        
        if category:
            query += ' AND c.name = ?'
            params.append(category)
        
        query += ' ORDER BY t.timestamp DESC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def delete_transaction(self, transaction_id: int, group_id: int) -> bool:
        """Delete a specific transaction. Returns True if successful."""
        try:
            # First check if transaction exists and belongs to the group
            self.cursor.execute(
                'SELECT id FROM transactions WHERE id = ? AND group_id = ?',
                (transaction_id, group_id)
            )
            if not self.cursor.fetchone():
                return False
            
            # Delete related exchange transaction if exists
            self.cursor.execute(
                'DELETE FROM exchange_transactions WHERE transaction_id = ?',
                (transaction_id,)
            )
            
            # Delete the transaction
            self.cursor.execute(
                'DELETE FROM transactions WHERE id = ?',
                (transaction_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            return False 

    def rename_category(self, old_name: str, new_name: str) -> bool:
        """Rename a category. Returns True if successful."""
        try:
            # Check if old category exists
            self.cursor.execute('SELECT id FROM categories WHERE name = ?', (old_name,))
            if not self.cursor.fetchone():
                return False, "La categoría original no existe"
            
            # Check if new name already exists
            self.cursor.execute('SELECT id FROM categories WHERE name = ?', (new_name,))
            if self.cursor.fetchone():
                return False, "Ya existe una categoría con ese nombre"
            
            # Rename the category
            self.cursor.execute(
                'UPDATE categories SET name = ? WHERE name = ?',
                (new_name, old_name)
            )
            self.conn.commit()
            return True, f"Categoría renombrada de '{old_name}' a '{new_name}'"
        except Exception as e:
            logger.error(f"Error renaming category: {e}")
            return False, "Error al renombrar la categoría" 

    def get_balance_by_money_type_and_currency(self, group_id: int, money_type_id: int, currency: str) -> float:
        """Get balance for a specific money type and currency."""
        try:
            if currency == 'USD':
                # Get all USD transactions (both regular and exchanges)
                self.cursor.execute('''
                    SELECT id, type, amount, description 
                    FROM transactions 
                    WHERE group_id = ? AND currency = 'USD'
                    ORDER BY timestamp
                ''', (group_id,))
                transactions = self.cursor.fetchall()
                logger.info("=== USD Transactions ===")
                for tx in transactions:
                    logger.info(f"ID: {tx[0]}, Type: {tx[1]}, Amount: {tx[2]}, Desc: {tx[3]}")

                # Calculate USD balance:
                # 1. Get all regular USD transactions (incomes and expenses)
                self.cursor.execute('''
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions
                    WHERE group_id = ? 
                    AND currency = 'USD'
                    AND NOT EXISTS (
                        SELECT 1 FROM exchange_transactions e 
                        WHERE e.transaction_id = transactions.id
                    )
                ''', (group_id,))
                regular_balance = self.cursor.fetchone()[0] or 0.0
                logger.info(f"Regular USD Balance: {regular_balance}")

                # 2. Get all USD amounts that were exchanged to ARS
                self.cursor.execute('''
                    SELECT COALESCE(SUM(e.source_amount), 0)
                    FROM exchange_transactions e
                    JOIN transactions t ON e.transaction_id = t.id
                    WHERE t.group_id = ? 
                    AND e.source_currency = 'USD'
                ''', (group_id,))
                exchanged_amount = self.cursor.fetchone()[0] or 0.0
                logger.info(f"USD Exchanged Amount: {exchanged_amount}")

                # Final balance is regular transactions minus exchanged amounts
                final_balance = regular_balance - exchanged_amount
                logger.info(f"Final USD Balance: {final_balance}")

                return final_balance
            else:
                # For ARS, calculate balance properly
                self.cursor.execute('''
                    SELECT COALESCE(SUM(amount), 0)  -- amount is already signed (-ve for expenses)
                    FROM transactions
                    WHERE group_id = ? 
                    AND money_type_id = ? 
                    AND currency = ?
                ''', (group_id, money_type_id, currency))
                balance = self.cursor.fetchone()[0] or 0.0
                logger.info(f"ARS Balance for money_type {money_type_id}: {balance}")
                return balance

        except Exception as e:
            logger.error(f"Error getting balance by money type and currency: {e}")
            return 0.0 