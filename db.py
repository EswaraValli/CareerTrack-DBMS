"""
Database initialization and connection module for CareerTrack PMS
Handles SQLite database setup, schema creation, and connection management
"""

import sqlite3
import os
from datetime import datetime

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), 'careertrack.db')

def get_db_connection():
    """
    Create and return a database connection with row factory enabled
    Returns:
        sqlite3.Connection: Database connection object
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

def init_database():
    """
    Initialize the database by creating all tables from SQL files
    Executes core_tables.sql, project_dump.sql, and indexes.sql
    """
    print("=" * 60)
    print("Initializing CareerTrack Database...")
    print("=" * 60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Get the sql directory path
    sql_dir = os.path.join(os.path.dirname(__file__), 'sql')
    
    # Execute SQL files in order
    sql_files = ['core_tables.sql', 'project_dump.sql', 'indexes.sql']
    
    for sql_file in sql_files:
        file_path = os.path.join(sql_dir, sql_file)
        
        if os.path.exists(file_path):
            print(f"\n✓ Executing {sql_file}...")
            with open(file_path, 'r') as f:
                sql_script = f.read()
                cursor.executescript(sql_script)
            print(f"  Successfully executed {sql_file}")
        else:
            print(f"\n✗ Warning: {sql_file} not found at {file_path}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print("Database initialization completed successfully!")
    print(f"Database location: {DB_PATH}")
    print("=" * 60)

def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """
    Execute a SQL query with optional parameters
    
    Args:
        query (str): SQL query to execute
        params (tuple): Query parameters
        fetch_one (bool): Return single row
        fetch_all (bool): Return all rows
        commit (bool): Commit changes to database
    
    Returns:
        Result of query execution
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if commit:
            conn.commit()
            result = cursor.lastrowid
        elif fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = None
        
        return result
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

def get_table_info(table_name):
    """
    Get column information for a specific table
    
    Args:
        table_name (str): Name of the table
    
    Returns:
        list: List of column information
    """
    query = f"PRAGMA table_info({table_name});"
    return execute_query(query, fetch_all=True)

def get_all_tables():
    """
    Get list of all tables in the database
    
    Returns:
        list: List of table names
    """
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    tables = execute_query(query, fetch_all=True)
    return [table['name'] for table in tables] if tables else []

def check_table_exists(table_name):
    """
    Check if a table exists in the database
    
    Args:
        table_name (str): Name of the table to check
    
    Returns:
        bool: True if table exists, False otherwise
    """
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
    result = execute_query(query, (table_name,), fetch_one=True)
    return result is not None

def reset_database():
    """
    Drop all tables and reinitialize the database
    WARNING: This will delete all data!
    """
    print("\n⚠️  WARNING: This will delete all data!")
    confirm = input("Type 'YES' to confirm database reset: ")
    
    if confirm == 'YES':
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print("✓ Existing database deleted")
        
        init_database()
        print("✓ Database reset completed")
    else:
        print("✗ Database reset cancelled")

def get_database_stats():
    """
    Get statistics about the database
    
    Returns:
        dict: Database statistics
    """
    stats = {}
    
    # Get all tables
    tables = get_all_tables()
    stats['total_tables'] = len(tables)
    stats['table_counts'] = {}
    
    # Get row count for each table
    for table in tables:
        try:
            query = f"SELECT COUNT(*) as count FROM {table};"
            result = execute_query(query, fetch_one=True)
            stats['table_counts'][table] = result['count'] if result else 0
        except:
            stats['table_counts'][table] = 0
    
    # Get database file size
    if os.path.exists(DB_PATH):
        stats['database_size_mb'] = round(os.path.getsize(DB_PATH) / (1024 * 1024), 2)
    else:
        stats['database_size_mb'] = 0
    
    return stats

if __name__ == "__main__":
    # Initialize database if run directly
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'reset':
        reset_database()
    else:
        init_database()
        
        # Print database statistics
        print("\nDatabase Statistics:")
        print("-" * 60)
        stats = get_database_stats()
        print(f"Total Tables: {stats['total_tables']}")
        print(f"Database Size: {stats['database_size_mb']} MB")
        print("\nTable Row Counts:")
        for table, count in stats['table_counts'].items():
            print(f"  {table:30s}: {count:5d} rows")
