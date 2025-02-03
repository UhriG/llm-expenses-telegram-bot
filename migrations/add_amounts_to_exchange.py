import sqlite3

def migrate(db_path='expenses.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create temporary table with new schema
        cursor.execute('''
            CREATE TABLE exchange_transactions_new (
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
        
        # Copy data from old table to new table
        cursor.execute('''
            INSERT INTO exchange_transactions_new (
                id, transaction_id, source_currency, target_currency, exchange_rate,
                source_amount, target_amount
            )
            SELECT 
                id, transaction_id, source_currency, target_currency, exchange_rate,
                0, 0  -- Default values for new columns
            FROM exchange_transactions
        ''')
        
        # Drop old table
        cursor.execute('DROP TABLE exchange_transactions')
        
        # Rename new table to original name
        cursor.execute('ALTER TABLE exchange_transactions_new RENAME TO exchange_transactions')
        
        conn.commit()
        print("Migration completed successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        
    finally:
        conn.close()

if __name__ == '__main__':
    migrate() 