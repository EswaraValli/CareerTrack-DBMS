"""
Setup script for CareerTrack PMS
Run this to ensure everything is configured correctly
"""

import os
import sqlite3
import hashlib

def hash_password(password):
    salt = 'careertrack_salt_2026'
    return hashlib.sha256((password + salt).encode()).hexdigest()

print("=" * 80)
print("CAREERTRACK PMS - SETUP & VERIFICATION")
print("=" * 80)

# Step 1: Check if database exists
db_path = 'careertrack.db'

if os.path.exists(db_path):
    print(f"\n✓ Database file found: {db_path}")
    print(f"  Size: {os.path.getsize(db_path)} bytes")
else:
    print(f"\n✗ Database file NOT found!")
    print("  Creating database...")
    import db
    db.init_database()

# Step 2: Verify users exist with correct passwords
print("\n" + "=" * 80)
print("VERIFYING USER ACCOUNTS")
print("=" * 80)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check users
cursor.execute('SELECT Username, PasswordHash, Role FROM Users WHERE Username IN (?, ?)', 
               ('admin', 'officer'))
users = cursor.fetchall()

users_dict = {user[0]: {'hash': user[1], 'role': user[2]} for user in users}

# Expected hashes
expected = {
    'admin': hash_password('admin123'),
    'officer': hash_password('officer123')
}

needs_fix = False

for username in ['admin', 'officer']:
    print(f"\n{username.upper()}:")
    
    if username not in users_dict:
        print(f"  ❌ User not found in database!")
        needs_fix = True
    else:
        stored_hash = users_dict[username]['hash']
        correct_hash = expected[username]
        
        if stored_hash == correct_hash:
            print(f"  ✅ Password hash is CORRECT")
            print(f"  Role: {users_dict[username]['role']}")
        else:
            print(f"  ❌ Password hash is WRONG!")
            print(f"  Stored:   {stored_hash[:40]}...")
            print(f"  Expected: {correct_hash[:40]}...")
            needs_fix = True

# Fix if needed
if needs_fix:
    print("\n" + "=" * 80)
    print("FIXING USER PASSWORDS")
    print("=" * 80)
    
    # Delete existing users
    cursor.execute("DELETE FROM Users WHERE Username IN ('admin', 'officer')")
    
    # Insert with correct hashes
    admin_hash = hash_password('admin123')
    officer_hash = hash_password('officer123')
    
    cursor.execute("""
        INSERT INTO Users (Username, PasswordHash, Role, Email, IsActive)
        VALUES (?, ?, ?, ?, 1)
    """, ('admin', admin_hash, 'Admin', 'admin@careertrack.com'))
    
    cursor.execute("""
        INSERT INTO Users (Username, PasswordHash, Role, Email, IsActive)
        VALUES (?, ?, ?, ?, 1)
    """, ('officer', officer_hash, 'PlacementOfficer', 'officer@careertrack.com'))
    
    conn.commit()
    
    print("\n✅ Users fixed successfully!")
else:
    print("\n✅ All users are configured correctly!")

conn.close()

# Step 3: Test authentication
print("\n" + "=" * 80)
print("TESTING AUTHENTICATION")
print("=" * 80)

from auth_utils import authenticate_user

tests = [
    ('admin', 'admin123'),
    ('officer', 'officer123')
]

all_pass = True

for username, password in tests:
    result = authenticate_user(username, password)
    
    if result and 'error' not in result:
        print(f"\n✅ {username.upper()} login: SUCCESS")
        print(f"   Role: {result['role']}")
    else:
        print(f"\n❌ {username.upper()} login: FAILED")
        all_pass = False

# Final summary
print("\n" + "=" * 80)
print("SETUP COMPLETE")
print("=" * 80)

if all_pass:
    print("\n🎉 Everything is working correctly!")
    print("\nYou can now:")
    print("  1. Run the application: python app.py")
    print("  2. Open browser: http://localhost:5000/login")
    print("  3. Login with:")
    print("     • admin / admin123")
    print("     • officer / officer123")
else:
    print("\n⚠️  Some tests failed!")
    print("Please run: python diagnose.py")
    print("for detailed diagnostics.")

print()
