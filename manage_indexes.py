"""
Remove Indexes Script
Use this to remove all indexes before benchmarking
"""

import sqlite3

def remove_all_indexes(db_path='careertrack.db'):
    """Remove all custom indexes from the database"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("REMOVING INDEXES FOR BENCHMARKING")
    print("=" * 80)
    
    # Get list of all indexes
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' 
        AND name NOT LIKE 'sqlite_%'
        AND name NOT LIKE '%autoindex%'
    """)
    
    indexes = cursor.fetchall()
    
    if not indexes:
        print("\nNo custom indexes found.")
    else:
        print(f"\nFound {len(indexes)} custom indexes:")
        for idx in indexes:
            print(f"  - {idx[0]}")
        
        print("\nDropping indexes...")
        for idx in indexes:
            try:
                cursor.execute(f"DROP INDEX IF EXISTS {idx[0]}")
                print(f"  ✓ Dropped {idx[0]}")
            except Exception as e:
                print(f"  ✗ Error dropping {idx[0]}: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ All indexes removed")
    print("\nNow run: python benchmark.py before")
    print("=" * 80)


def apply_indexes(db_path='careertrack.db'):
    """Apply all indexes from indexes.sql"""
    
    import os
    
    print("=" * 80)
    print("APPLYING INDEXES")
    print("=" * 80)
    
    indexes_file = 'sql/indexes.sql'
    
    if not os.path.exists(indexes_file):
        print(f"Error: {indexes_file} not found!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(indexes_file, 'r') as f:
        sql_script = f.read()
    
    print(f"\nExecuting {indexes_file}...")
    cursor.executescript(sql_script)
    
    conn.commit()
    
    # Count indexes
    cursor.execute("""
        SELECT COUNT(*) FROM sqlite_master 
        WHERE type='index' 
        AND name NOT LIKE 'sqlite_%'
        AND name NOT LIKE '%autoindex%'
    """)
    
    count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n✅ Indexes applied successfully!")
    print(f"Total custom indexes: {count}")
    print("\nNow run: python benchmark.py after")
    print("=" * 80)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_indexes.py remove   - Remove all indexes")
        print("  python manage_indexes.py apply    - Apply all indexes")
        sys.exit(1)
    
    action = sys.argv[1].lower()
    
    if action == 'remove':
        remove_all_indexes()
    elif action == 'apply':
        apply_indexes()
    else:
        print(f"Unknown action: {action}")
        print("Use 'remove' or 'apply'")
