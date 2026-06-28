"""
Authentication and Session Management Utilities for CareerTrack PMS
Handles password hashing, session token generation, and validation
"""

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from db import get_db_connection

# Session configuration
SESSION_TIMEOUT_HOURS = 24

def hash_password(password):
    """
    Hash a password using SHA-256
    
    Args:
        password (str): Plain text password
    
    Returns:
        str: Hashed password
    """
    # Simple SHA-256 hashing (in production, use bcrypt or scrypt)
    salt = "careertrack_salt_2026"  # In production, use random salt per user
    return hashlib.sha256((password + salt).encode()).hexdigest()

def verify_password(stored_hash, provided_password):
    """
    Verify a password against stored hash
    
    Args:
        stored_hash (str): Stored password hash
        provided_password (str): Password to verify
    
    Returns:
        bool: True if password matches, False otherwise
    """
    return stored_hash == hash_password(provided_password)

def generate_session_token():
    """
    Generate a secure random session token
    
    Returns:
        str: Secure random token
    """
    return secrets.token_urlsafe(32)

def create_session(user_id, username, role):
    """
    Create a new session for a user
    
    Args:
        user_id (int): User ID
        username (str): Username
        role (str): User role
    
    Returns:
        dict: Session information including token
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Generate session token
    session_token = generate_session_token()
    
    # Calculate expiry time
    expires_at = datetime.now() + timedelta(hours=SESSION_TIMEOUT_HOURS)
    
    # Invalidate any existing sessions for this user
    cursor.execute("""
        UPDATE Sessions 
        SET IsValid = 0 
        WHERE UserID = ? AND IsValid = 1
    """, (user_id,))
    
    # Insert new session
    cursor.execute("""
        INSERT INTO Sessions (UserID, SessionToken, ExpiresAt, IsValid)
        VALUES (?, ?, ?, 1)
    """, (user_id, session_token, expires_at))
    
    # Update last login time
    cursor.execute("""
        UPDATE Users 
        SET LastLogin = ? 
        WHERE UserID = ?
    """, (datetime.now(), user_id))
    
    conn.commit()
    conn.close()
    
    return {
        'session_token': session_token,
        'username': username,
        'role': role,
        'expires_at': expires_at.isoformat(),
        'user_id': user_id
    }

def validate_session(session_token):
    """
    Validate a session token
    
    Args:
        session_token (str): Session token to validate
    
    Returns:
        dict: Session information if valid, None otherwise
    """
    if not session_token:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query session and user information
    cursor.execute("""
        SELECT s.SessionID, s.UserID, s.ExpiresAt, u.Username, u.Role, u.Email
        FROM Sessions s
        JOIN Users u ON s.UserID = u.UserID
        WHERE s.SessionToken = ? AND s.IsValid = 1
    """, (session_token,))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return None
    
    # Check if session has expired
    expires_at = datetime.fromisoformat(result['ExpiresAt'])
    if datetime.now() > expires_at:
        # Invalidate expired session
        invalidate_session(session_token)
        return None
    
    return {
        'user_id': result['UserID'],
        'username': result['Username'],
        'role': result['Role'],
        'email': result['Email'],
        'expires_at': result['ExpiresAt']
    }

def invalidate_session(session_token):
    """
    Invalidate a session (logout)
    
    Args:
        session_token (str): Session token to invalidate
    
    Returns:
        bool: True if session was invalidated
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE Sessions 
        SET IsValid = 0 
        WHERE SessionToken = ?
    """, (session_token,))
    
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    return affected > 0

def authenticate_user(username, password):
    """
    Authenticate a user with username and password
    
    Args:
        username (str): Username
        password (str): Password
    
    Returns:
        dict: Session information if authentication successful, None otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query user
    cursor.execute("""
        SELECT UserID, Username, PasswordHash, Role, Email, IsActive
        FROM Users
        WHERE Username = ?
    """, (username,))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return None
    
    # Check if user is active
    if not user['IsActive']:
        return {'error': 'Account is deactivated'}
    
    # Verify password
    if not verify_password(user['PasswordHash'], password):
        return None
    
    # Create session
    return create_session(user['UserID'], user['Username'], user['Role'])

def require_auth(f):
    """
    Decorator to require authentication for API endpoints
    
    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route():
            # Access current_user from request
            user = request.current_user
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get session token from request
        session_token = request.headers.get('Authorization')
        
        if session_token and session_token.startswith('Bearer '):
            session_token = session_token[7:]  # Remove 'Bearer ' prefix
        else:
            session_token = request.json.get('session_token') if request.is_json else None
        
        # Validate session
        session = validate_session(session_token)
        
        if not session:
            return jsonify({'error': 'Unauthorized', 'message': 'Invalid or expired session'}), 401
        
        # Attach user info to request
        request.current_user = session
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_role(*allowed_roles):
    """
    Decorator to require specific roles for API endpoints
    
    Usage:
        @app.route('/admin-only')
        @require_auth
        @require_role('Admin', 'PlacementOfficer')
        def admin_route():
            # Only admins and placement officers can access
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(request, 'current_user', None)
            
            if not user:
                return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
            
            if user['role'] not in allowed_roles:
                return jsonify({
                    'error': 'Forbidden',
                    'message': f'This action requires one of these roles: {", ".join(allowed_roles)}'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator

def get_user_by_id(user_id):
    """
    Get user information by user ID
    
    Args:
        user_id (int): User ID
    
    Returns:
        dict: User information
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT UserID, Username, Role, Email, CreatedAt, LastLogin, IsActive
        FROM Users
        WHERE UserID = ?
    """, (user_id,))
    
    user = cursor.fetchone()
    conn.close()
    
    return dict(user) if user else None

def create_user(username, password, role, email):
    """
    Create a new user account
    
    Args:
        username (str): Username
        password (str): Password
        role (str): User role
        email (str): Email address
    
    Returns:
        dict: Created user information or error
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if username or email already exists
        cursor.execute("""
            SELECT UserID FROM Users 
            WHERE Username = ? OR Email = ?
        """, (username, email))
        
        if cursor.fetchone():
            return {'error': 'Username or email already exists'}
        
        # Hash password
        password_hash = hash_password(password)
        
        # Insert user
        cursor.execute("""
            INSERT INTO Users (Username, PasswordHash, Role, Email)
            VALUES (?, ?, ?, ?)
        """, (username, password_hash, role, email))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        return {
            'user_id': user_id,
            'username': username,
            'role': role,
            'email': email
        }
    
    except sqlite3.IntegrityError as e:
        return {'error': f'Database error: {str(e)}'}
    
    finally:
        conn.close()
