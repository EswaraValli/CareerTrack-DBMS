"""
Analytics API Routes for CareerTrack PMS
"""

from flask import request, jsonify
from routes import analytics_bp
from auth_utils import require_auth, require_role
from db import get_db_connection

@analytics_bp.route('/placement-stats', methods=['GET'])
@require_auth
def get_placement_statistics():
    """Get placement statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # Total students
    cursor.execute("SELECT COUNT(*) as count FROM Student")
    stats['total_students'] = cursor.fetchone()['count']
    
    # Placed students
    cursor.execute("SELECT COUNT(*) as count FROM Student WHERE IsPlaced = 1")
    stats['placed_students'] = cursor.fetchone()['count']
    
    # Placement percentage
    if stats['total_students'] > 0:
        stats['placement_percentage'] = round((stats['placed_students'] / stats['total_students']) * 100, 2)
    else:
        stats['placement_percentage'] = 0
    
    # Average package
    cursor.execute("SELECT AVG(FinalPackage) as avg_package FROM PlacementOffer WHERE AcceptanceStatus = 'Accepted'")
    result = cursor.fetchone()
    stats['average_package'] = round(result['avg_package'], 2) if result['avg_package'] else 0
    
    # Highest package
    cursor.execute("SELECT MAX(FinalPackage) as max_package FROM PlacementOffer WHERE AcceptanceStatus = 'Accepted'")
    result = cursor.fetchone()
    stats['highest_package'] = result['max_package'] if result['max_package'] else 0
    
    # Top companies by placements
    cursor.execute("""
        SELECT c.CompanyName, COUNT(*) as placement_count
        FROM PlacementOffer po
        JOIN Company c ON po.CompanyID = c.CompanyID
        WHERE po.AcceptanceStatus = 'Accepted'
        GROUP BY c.CompanyID
        ORDER BY placement_count DESC
        LIMIT 5
    """)
    stats['top_companies'] = [dict(row) for row in cursor.fetchall()]
    
    # Department-wise placement
    cursor.execute("""
        SELECT d.DeptName, 
               COUNT(DISTINCT s.StudentID) as total_students,
               COUNT(DISTINCT CASE WHEN s.IsPlaced = 1 THEN s.StudentID END) as placed_students
        FROM Department d
        LEFT JOIN Student s ON d.DeptID = s.DeptID
        GROUP BY d.DeptID
    """)
    stats['department_wise'] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(stats), 200

@analytics_bp.route('/job-stats', methods=['GET'])
@require_auth
def get_job_statistics():
    """Get job posting statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # Total active jobs
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM JobPosting 
        WHERE Deadline IS NULL OR Deadline >= DATE('now')
    """)
    stats['active_jobs'] = cursor.fetchone()['count']
    
    # Total applications
    cursor.execute("SELECT COUNT(*) as count FROM Application")
    stats['total_applications'] = cursor.fetchone()['count']
    
    # Applications by status
    cursor.execute("""
        SELECT Status, COUNT(*) as count
        FROM Application
        GROUP BY Status
    """)
    stats['applications_by_status'] = [dict(row) for row in cursor.fetchall()]
    
    # Jobs by company
    cursor.execute("""
        SELECT c.CompanyName, COUNT(j.JobID) as job_count
        FROM Company c
        LEFT JOIN JobPosting j ON c.CompanyID = j.CompanyID
        GROUP BY c.CompanyID
        ORDER BY job_count DESC
        LIMIT 10
    """)
    stats['jobs_by_company'] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(stats), 200

@analytics_bp.route('/student-performance', methods=['GET'])
@require_auth
@require_role('Admin', 'PlacementOfficer')
def get_student_performance():
    """Get student performance analytics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # CGPA distribution
    cursor.execute("""
        SELECT 
            CASE 
                WHEN CGPA >= 9.0 THEN '9.0+'
                WHEN CGPA >= 8.0 THEN '8.0-8.9'
                WHEN CGPA >= 7.0 THEN '7.0-7.9'
                WHEN CGPA >= 6.0 THEN '6.0-6.9'
                ELSE 'Below 6.0'
            END as cgpa_range,
            COUNT(*) as count
        FROM Student
        GROUP BY cgpa_range
        ORDER BY cgpa_range DESC
    """)
    
    cgpa_dist = [dict(row) for row in cursor.fetchall()]
    
    # Top students by CGPA
    cursor.execute("""
        SELECT s.Name, s.CGPA, d.DeptName, s.IsPlaced
        FROM Student s
        LEFT JOIN Department d ON s.DeptID = d.DeptID
        ORDER BY s.CGPA DESC
        LIMIT 10
    """)
    
    top_students = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify({
        'cgpa_distribution': cgpa_dist,
        'top_students': top_students
    }), 200
