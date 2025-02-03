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
        # ... (keep existing table creation code)

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
        # ... (keep existing implementation)

    # ... (keep all other existing database methods) 