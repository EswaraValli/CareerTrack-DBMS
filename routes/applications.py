"""
Applications API Routes for CareerTrack PMS
"""

from flask import request, jsonify
from routes import applications_bp
from auth_utils import require_auth, require_role
from audit import log_data_modification
from db import get_db_connection

@applications_bp.route('/', methods=['GET'])
@require_auth
def get_applications():
    """
    Get applications
    Students: their own applications
    Admin/Officer: all applications
    """
    user = request.current_user
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if user['role'] in ['Admin', 'PlacementOfficer']:
        cursor.execute("""
            SELECT a.*, s.Name as StudentName, j.RoleTitle, c.CompanyName
            FROM Application a
            JOIN Student s ON a.StudentID = s.StudentID
            JOIN JobPosting j ON a.JobID = j.JobID
            JOIN Company c ON j.CompanyID = c.CompanyID
            ORDER BY a.ApplyDate DESC
        """)
    else:
        # Get student's own applications
        cursor.execute("""
            SELECT a.*, s.Name as StudentName, j.RoleTitle, c.CompanyName, j.Package_LPA
            FROM Application a
            JOIN Student s ON a.StudentID = s.StudentID
            JOIN JobPosting j ON a.JobID = j.JobID
            JOIN Company c ON j.CompanyID = c.CompanyID
            WHERE s.UserID = ?
            ORDER BY a.ApplyDate DESC
        """, (user['user_id'],))
    
    applications = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(applications), 200

@applications_bp.route('/', methods=['POST'])
@require_auth
@require_role('Student')
def apply_for_job():
    """Student applies for a job"""
    user = request.current_user
    data = request.get_json()
    
    if 'job_id' not in data:
        return jsonify({'error': 'Missing job_id'}), 400
    
    job_id = data['job_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get student ID
        cursor.execute("SELECT StudentID, CGPA, IsPlaced FROM Student WHERE UserID = ?", 
                      (user['user_id'],))
        student = cursor.fetchone()
        
        if not student:
            conn.close()
            return jsonify({'error': 'Student profile not found'}), 404
        
        # Check if already placed
        if student['IsPlaced']:
            conn.close()
            return jsonify({'error': 'You are already placed'}), 400
        
        # Check eligibility
        cursor.execute("SELECT MinCGPA, Deadline FROM JobPosting WHERE JobID = ?", (job_id,))
        job = cursor.fetchone()
        
        if not job:
            conn.close()
            return jsonify({'error': 'Job not found'}), 404
        
        if student['CGPA'] < job['MinCGPA']:
            conn.close()
            return jsonify({'error': f'CGPA requirement not met. Minimum: {job["MinCGPA"]}'}), 400
        
        # Check if already applied
        cursor.execute("""
            SELECT AppID FROM Application 
            WHERE StudentID = ? AND JobID = ?
        """, (student['StudentID'], job_id))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Already applied for this job'}), 400
        
        # Create application
        cursor.execute("""
            INSERT INTO Application (StudentID, JobID, Status)
            VALUES (?, ?, 'Applied')
        """, (student['StudentID'], job_id))
        
        app_id = cursor.lastrowid
        conn.commit()
        
        log_data_modification(
            user['user_id'], user['username'], 'INSERT', 'Application', app_id, 
            new_data={'StudentID': student['StudentID'], 'JobID': job_id}
        )
        
        return jsonify({'message': 'Application submitted', 'app_id': app_id}), 201
    
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@applications_bp.route('/<int:app_id>/status', methods=['PUT'])
@require_auth
@require_role('Admin', 'PlacementOfficer')
def update_application_status(app_id):
    """Update application status (Admin/Officer only)"""
    user = request.current_user
    data = request.get_json()
    
    if 'status' not in data:
        return jsonify({'error': 'Missing status'}), 400
    
    status = data['status']
    valid_statuses = ['Applied', 'Shortlisted', 'Rejected', 'Selected', 'Withdrawn']
    
    if status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE Application SET Status = ? WHERE AppID = ?", (status, app_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Application not found'}), 404
        
        conn.commit()
        
        log_data_modification(
            user['user_id'], user['username'], 'UPDATE', 'Application', app_id,
            new_data={'Status': status}
        )
        
        return jsonify({'message': 'Application status updated'}), 200
    
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@applications_bp.route('/job/<int:job_id>', methods=['GET'])
@require_auth
@require_role('Admin', 'PlacementOfficer', 'Company')
def get_job_applications(job_id):
    """Get all applications for a specific job"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT a.*, s.Name, s.Email, s.CGPA, s.GraduationYear, d.DeptName
        FROM Application a
        JOIN Student s ON a.StudentID = s.StudentID
        LEFT JOIN Department d ON s.DeptID = d.DeptID
        WHERE a.JobID = ?
        ORDER BY s.CGPA DESC, a.ApplyDate
    """, (job_id,))
    
    applications = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(applications), 200
