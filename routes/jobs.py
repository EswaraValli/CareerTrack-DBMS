"""
Job Postings API Routes for CareerTrack PMS
"""

from flask import request, jsonify
from routes import jobs_bp
from auth_utils import require_auth, require_role
from audit import log_data_modification
from db import get_db_connection

@jobs_bp.route('/', methods=['GET'])
@require_auth
def get_all_jobs():
    """Get all job postings"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT j.*, c.CompanyName, pd.DriveName
        FROM JobPosting j
        LEFT JOIN Company c ON j.CompanyID = c.CompanyID
        LEFT JOIN PlacementDrive pd ON j.DriveID = pd.DriveID
        ORDER BY j.PostDate DESC
    """)
    
    jobs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(jobs), 200

@jobs_bp.route('/eligible', methods=['GET'])
@require_auth
@require_role('Student')
def get_eligible_jobs():
    """Get jobs eligible for current student based on CGPA"""
    user = request.current_user
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get student's CGPA
    cursor.execute("SELECT CGPA FROM Student WHERE UserID = ?", (user['user_id'],))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return jsonify({'error': 'Student profile not found'}), 404
    
    # Get eligible jobs
    cursor.execute("""
        SELECT j.*, c.CompanyName, pd.DriveName
        FROM JobPosting j
        LEFT JOIN Company c ON j.CompanyID = c.CompanyID
        LEFT JOIN PlacementDrive pd ON j.DriveID = pd.DriveID
        WHERE j.MinCGPA <= ?
        AND (j.Deadline IS NULL OR j.Deadline >= DATE('now'))
        ORDER BY j.PostDate DESC
    """, (student['CGPA'],))
    
    jobs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(jobs), 200

@jobs_bp.route('/<int:job_id>', methods=['GET'])
@require_auth
def get_job(job_id):
    """Get single job details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT j.*, c.CompanyName, c.Website, c.Industry, c.Location, pd.DriveName
        FROM JobPosting j
        LEFT JOIN Company c ON j.CompanyID = c.CompanyID
        LEFT JOIN PlacementDrive pd ON j.DriveID = pd.DriveID
        WHERE j.JobID = ?
    """, (job_id,))
    
    job = cursor.fetchone()
    conn.close()
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(dict(job)), 200

@jobs_bp.route('/', methods=['POST'])
@require_auth
@require_role('Admin', 'PlacementOfficer', 'Company')
def create_job():
    """Create new job posting"""
    user = request.current_user
    data = request.get_json()
    
    required = ['CompanyID', 'RoleTitle', 'MinCGPA']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO JobPosting (CompanyID, DriveID, RoleTitle, Description, 
                                   Package_LPA, MinCGPA, Deadline, JobType)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (data['CompanyID'], data.get('DriveID'), data['RoleTitle'],
              data.get('Description'), data.get('Package_LPA'), data['MinCGPA'],
              data.get('Deadline'), data.get('JobType')))
        
        job_id = cursor.lastrowid
        conn.commit()
        
        log_data_modification(
            user['user_id'], user['username'], 'INSERT', 'JobPosting', job_id, new_data=data
        )
        
        return jsonify({'message': 'Job created', 'job_id': job_id}), 201
    
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@jobs_bp.route('/<int:job_id>', methods=['PUT'])
@require_auth
@require_role('Admin', 'PlacementOfficer')
def update_job(job_id):
    """Update job posting"""
    user = request.current_user
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    allowed_fields = ['RoleTitle', 'Description', 'Package_LPA', 'MinCGPA', 'Deadline', 'JobType']
    updates = []
    values = []
    
    for field in allowed_fields:
        if field in data:
            updates.append(f"{field} = ?")
            values.append(data[field])
    
    if not updates:
        conn.close()
        return jsonify({'error': 'No valid fields to update'}), 400
    
    values.append(job_id)
    query = f"UPDATE JobPosting SET {', '.join(updates)} WHERE JobID = ?"
    
    try:
        cursor.execute(query, values)
        conn.commit()
        
        log_data_modification(
            user['user_id'], user['username'], 'UPDATE', 'JobPosting', job_id, new_data=data
        )
        
        return jsonify({'message': 'Job updated'}), 200
    
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
