"""
Audit Logging Module for CareerTrack PMS
Tracks all database modifications and API access for security monitoring
"""

import sqlite3
from datetime import datetime, timedelta  # timedelta imported here (was missing in original)
from flask import request
from db import get_db_connection


def log_audit(user_id, username, action, table_name=None, record_id=None,
              old_value=None, new_value=None, is_authorized=True):
    """
    Log an audit entry for database operations

    Args:
        user_id (int): ID of user performing action
        username (str): Username performing action
        action (str): Action performed (INSERT, UPDATE, DELETE, SELECT, etc.)
        table_name (str): Table affected
        record_id (int): ID of record affected
        old_value (str): Old value (for updates)
        new_value (str): New value (for updates/inserts)
        is_authorized (bool): Whether the action was authorized through API

    Returns:
        int: Audit log ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        ip_address = request.remote_addr if request else None
    except RuntimeError:
        # Outside of request context (e.g. called from tests)
        ip_address = None

    cursor.execute("""
        INSERT INTO AuditLog
        (UserID, Username, Action, TableName, RecordID, OldValue, NewValue, IPAddress, IsAuthorized)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, username, action, table_name, record_id,
          old_value, new_value, ip_address, is_authorized))

    log_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return log_id


def log_login_attempt(username, success, ip_address=None):
    """Log a login attempt"""
    action = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
    log_audit(None, username, action, is_authorized=success)


def log_api_access(user_id, username, endpoint, method, params=None):
    """Log API endpoint access"""
    action = f"API_{method}_{endpoint}"
    new_value = str(params) if params else None
    log_audit(user_id, username, action, new_value=new_value)


def log_data_modification(user_id, username, action, table_name, record_id,
                           old_data=None, new_data=None):
    """Log data modification (INSERT, UPDATE, DELETE)"""
    old_value = str(old_data) if old_data else None
    new_value = str(new_data) if new_data else None
    log_audit(user_id, username, action, table_name, record_id, old_value, new_value)


def get_audit_logs(limit=100, user_id=None, table_name=None, action=None,
                   start_date=None, end_date=None, unauthorized_only=False):
    """Retrieve audit logs with optional filtering"""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM AuditLog WHERE 1=1"
    params = []

    if user_id:
        query += " AND UserID = ?"
        params.append(user_id)
    if table_name:
        query += " AND TableName = ?"
        params.append(table_name)
    if action:
        query += " AND Action = ?"
        params.append(action)
    if start_date:
        query += " AND Timestamp >= ?"
        params.append(start_date)
    if end_date:
        query += " AND Timestamp <= ?"
        params.append(end_date)
    if unauthorized_only:
        query += " AND IsAuthorized = 0"

    query += " ORDER BY Timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    logs = cursor.fetchall()
    conn.close()

    return [dict(log) for log in logs]


def get_user_activity(user_id, days=7):
    """Get recent activity for a specific user"""
    start_date = datetime.now() - timedelta(days=days)   # fixed: timedelta now imported at top
    return get_audit_logs(user_id=user_id, start_date=start_date.isoformat())


def get_table_modifications(table_name, days=7):
    """Get recent modifications to a specific table"""
    start_date = datetime.now() - timedelta(days=days)
    return get_audit_logs(table_name=table_name, start_date=start_date.isoformat())


def get_unauthorized_attempts(days=7):
    """Get all unauthorized access attempts in recent days"""
    start_date = datetime.now() - timedelta(days=days)
    return get_audit_logs(
        unauthorized_only=True,
        start_date=start_date.isoformat(),
        limit=1000
    )


def export_audit_logs_to_file(filename='audit_export.log', days=30):
    """Export audit logs to a file"""
    import os
    start_date = datetime.now() - timedelta(days=days)
    logs = get_audit_logs(start_date=start_date.isoformat(), limit=10000)

    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    filepath = os.path.join(logs_dir, filename)

    with open(filepath, 'w') as f:
        f.write("CareerTrack PMS - Audit Log Export\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Period: Last {days} days\n")
        f.write("=" * 100 + "\n\n")

        for log in logs:
            f.write(f"[{log['Timestamp']}] ")
            f.write(f"User: {log['Username']} (ID: {log['UserID']}) | ")
            f.write(f"Action: {log['Action']} | ")
            if log['TableName']:
                f.write(f"Table: {log['TableName']} | ")
            if log['RecordID']:
                f.write(f"Record: {log['RecordID']} | ")
            f.write(f"Authorized: {'Yes' if log['IsAuthorized'] else 'NO'} | ")
            if log['IPAddress']:
                f.write(f"IP: {log['IPAddress']}")
            f.write("\n")
            if log['OldValue']:
                f.write(f"  Old Value: {log['OldValue']}\n")
            if log['NewValue']:
                f.write(f"  New Value: {log['NewValue']}\n")
            f.write("\n")

    return filepath


def get_audit_statistics():
    """Get statistics about audit logs"""
    conn = get_db_connection()
    cursor = conn.cursor()
    stats = {}

    cursor.execute("SELECT COUNT(*) as count FROM AuditLog")
    stats['total_logs'] = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM AuditLog WHERE IsAuthorized = 0")
    stats['unauthorized_attempts'] = cursor.fetchone()['count']

    cursor.execute("""
        SELECT Action, COUNT(*) as count
        FROM AuditLog
        GROUP BY Action
        ORDER BY count DESC
        LIMIT 10
    """)
    stats['top_actions'] = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT Username, COUNT(*) as count
        FROM AuditLog
        WHERE Username IS NOT NULL
        GROUP BY Username
        ORDER BY count DESC
        LIMIT 10
    """)
    stats['most_active_users'] = [dict(row) for row in cursor.fetchall()]

    yesterday = datetime.now() - timedelta(hours=24)
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM AuditLog
        WHERE Timestamp >= ?
    """, (yesterday.isoformat(),))
    stats['last_24h_activity'] = cursor.fetchone()['count']

    conn.close()
    return stats


if __name__ == "__main__":
    print("Audit Log Test")
    print("=" * 60)
    stats = get_audit_statistics()
    print(f"\nTotal Logs: {stats['total_logs']}")
    print(f"Unauthorized Attempts: {stats['unauthorized_attempts']}")
    print(f"Last 24h Activity: {stats['last_24h_activity']}")
    filepath = export_audit_logs_to_file()
    print(f"\nAudit logs exported to: {filepath}")
