"""
Authentication API Routes for CareerTrack PMS
Handles login, logout, session validation, and user registration
"""

from flask import request, jsonify
from routes import auth_bp
from auth_utils import (
    authenticate_user, 
    validate_session, 
    invalidate_session,
    create_user,
    require_auth,
    require_role
)
from audit import log_login_attempt, log_api_access, log_audit

@auth_bp.route('/', methods=['GET'])
def welcome():
    """
    Welcome endpoint
    """
    return jsonify({
        'message': 'Welcome to CareerTrack PMS API',
        'version': '1.0',
        'endpoints': {
            'login': '/api/auth/login',
            'logout': '/api/auth/logout',
            'isAuth': '/api/auth/isAuth',
            'register': '/api/auth/register'
        }
    })

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login endpoint
    
    POST /api/auth/login
    Request Body:
        {
            "username": "string",
            "password": "string"
        }
    
    Returns:
        200: {
            "message": "Login successful",
            "session_token": "string",
            "username": "string",
            "role": "string",
            "user_id": int,
            "expires_at": "datetime"
        }
        401: {"error": "Invalid credentials"}
    """
    # Debug logging
    print(f"\n{'='*80}")
    print(f"LOGIN REQUEST RECEIVED")
    print(f"{'='*80}")
    print(f"Request method: {request.method}")
    print(f"Request headers: {dict(request.headers)}")
    print(f"Request data (raw): {request.data}")
    print(f"Request JSON: {request.get_json()}")
    
    data = request.get_json()
    
    print(f"Parsed data: {data}")
    
    if not data:
        print("DEBUG: No data received - returning 400")
        return jsonify({'error': 'Missing parameters'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    print(f"Extracted - Username: '{username}', Password: {'*' * len(password) if password else 'None'}")
    
    if not username or not password:
        print(f"DEBUG: Missing fields - username: {bool(username)}, password: {bool(password)}")
        return jsonify({'error': 'Missing username or password'}), 400
    
    # Authenticate user
    result = authenticate_user(username, password)
    
    if not result:
        log_login_attempt(username, success=False, ip_address=request.remote_addr)
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if 'error' in result:
        return jsonify(result), 401
    
    # Log successful login
    log_login_attempt(username, success=True, ip_address=request.remote_addr)
    
    return jsonify({
        'message': 'Login successful',
        **result
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """
    User logout endpoint
    
    POST /api/auth/logout
    Headers:
        Authorization: Bearer {session_token}
    
    Returns:
        200: {"message": "Logout successful"}
        401: {"error": "Invalid session"}
    """
    user = request.current_user
    session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    # Invalidate session
    success = invalidate_session(session_token)
    
    if success:
        log_audit(
            user['user_id'], 
            user['username'], 
            'LOGOUT',
            is_authorized=True
        )
        return jsonify({'message': 'Logout successful'}), 200
    else:
        return jsonify({'error': 'Failed to logout'}), 500

@auth_bp.route('/isAuth', methods=['GET', 'POST'])
def is_authenticated():
    """
    Check if user session is valid
    
    GET /api/auth/isAuth
    Headers:
        Authorization: Bearer {session_token}
    
    OR
    
    POST /api/auth/isAuth
    Request Body:
        {
            "session_token": "string"
        }
    
    Returns:
        200: {
            "message": "User is authenticated",
            "username": "string",
            "role": "string",
            "user_id": int,
            "email": "string",
            "expires_at": "datetime"
        }
        401: {"error": "Not authenticated"}
    """
    # Get session token from header or body
    session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not session_token and request.is_json:
        session_token = request.get_json().get('session_token')
    
    if not session_token:
        return jsonify({'error': 'No session token provided'}), 401
    
    # Validate session
    session = validate_session(session_token)
    
    if not session:
        return jsonify({'error': 'Session expired or invalid'}), 401
    
    return jsonify({
        'message': 'User is authenticated',
        **session
    }), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user (open registration for students)
    For company/admin registration, use admin endpoints
    
    POST /api/auth/register
    Request Body:
        {
            "username": "string",
            "password": "string",
            "email": "string",
            "role": "Student" (default)
        }
    
    Returns:
        201: {
            "message": "User registered successfully",
            "user_id": int,
            "username": "string"
        }
        400: {"error": "Username or email already exists"}
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing parameters'}), 400
    
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    role = data.get('role', 'Student')  # Default to Student role
    
    # Validate required fields
    if not username or not password or not email:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Only allow Student role for public registration
    if role not in ['Student']:
        return jsonify({'error': 'Invalid role for registration'}), 400
    
    # Create user
    result = create_user(username, password, role, email)
    
    if 'error' in result:
        return jsonify(result), 400
    
    # Log registration
    log_audit(
        result['user_id'],
        username,
        'USER_REGISTERED',
        table_name='Users',
        record_id=result['user_id'],
        is_authorized=True
    )
    
    return jsonify({
        'message': 'User registered successfully',
        **result
    }), 201

@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password():
    """
    Change user password
    
    POST /api/auth/change-password
    Headers:
        Authorization: Bearer {session_token}
    Request Body:
        {
            "old_password": "string",
            "new_password": "string"
        }
    
    Returns:
        200: {"message": "Password changed successfully"}
        400: {"error": "Invalid old password"}
    """
    from auth_utils import verify_password, hash_password
    from db import get_db_connection
    
    user = request.current_user
    data = request.get_json()
    
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Get current password hash
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT PasswordHash FROM Users WHERE UserID = ?", (user['user_id'],))
    result = cursor.fetchone()
    
    if not result or not verify_password(result['PasswordHash'], old_password):
        conn.close()
        return jsonify({'error': 'Invalid old password'}), 400
    
    # Update password
    new_hash = hash_password(new_password)
    cursor.execute("UPDATE Users SET PasswordHash = ? WHERE UserID = ?", 
                  (new_hash, user['user_id']))
    conn.commit()
    conn.close()
    
    # Log password change
    log_audit(
        user['user_id'],
        user['username'],
        'PASSWORD_CHANGED',
        table_name='Users',
        record_id=user['user_id'],
        is_authorized=True
    )
    
    return jsonify({'message': 'Password changed successfully'}), 200
