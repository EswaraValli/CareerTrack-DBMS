"""
Admin API Routes for CareerTrack PMS
"""

from flask import request, jsonify
from routes import admin_bp
from auth_utils import require_auth, require_role, create_user
from audit import get_audit_logs, get_audit_statistics, export_audit_logs_to_file
from db import get_db_connection, get_database_stats

@admin_bp.route('/users', methods=['GET'])
@require_auth
@require_role('Admin')
def get_all_users():
    """Get all users (Admin only)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT UserID, Username, Role, Email, CreatedAt, LastLogin, IsActive
        FROM Users
        ORDER BY CreatedAt DESC
    """)
    
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(users), 200

@admin_bp.route('/users', methods=['POST'])
@require_auth
@require_role('Admin')
def create_new_user():
    """Create new user (Admin only)"""
    data = request.get_json()
    
    required = ['username', 'password', 'role', 'email']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    result = create_user(data['username'], data['password'], data['role'], data['email'])
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify({
        'message': 'User created successfully',
        **result
    }), 201

@admin_bp.route('/audit-logs', methods=['GET'])
@require_auth
@require_role('Admin', 'PlacementOfficer')
def get_audit():
    """Get audit logs"""
    limit = request.args.get('limit', 100, type=int)
    user_id = request.args.get('user_id', type=int)
    table_name = request.args.get('table_name')
    unauthorized_only = request.args.get('unauthorized_only', 'false').lower() == 'true'
    
    logs = get_audit_logs(
        limit=limit,
        user_id=user_id,
        table_name=table_name,
        unauthorized_only=unauthorized_only
    )
    
    return jsonify(logs), 200

@admin_bp.route('/audit-stats', methods=['GET'])
@require_auth
@require_role('Admin')
def get_audit_stats():
    """Get audit statistics"""
    stats = get_audit_statistics()
    return jsonify(stats), 200

@admin_bp.route('/database-stats', methods=['GET'])
@require_auth
@require_role('Admin')
def get_db_stats():
    """Get database statistics"""
    stats = get_database_stats()
    return jsonify(stats), 200

@admin_bp.route('/export-audit', methods=['POST'])
@require_auth
@require_role('Admin')
def export_audit():
    """Export audit logs to file"""
    days = request.get_json().get('days', 30)
    filepath = export_audit_logs_to_file(days=days)
    return jsonify({'message': 'Audit logs exported', 'filepath': filepath}), 200
