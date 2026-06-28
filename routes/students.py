"""
Student/Member API Routes for CareerTrack PMS
Handles student profile management and portfolio
"""

from flask import request, jsonify
from routes import students_bp
from auth_utils import require_auth, require_role
from audit import log_data_modification
from db import get_db_connection

@students_bp.route('/', methods=['GET'])
@require_auth
def get_all_students():
    """
    Get all students (Member Portfolio)
    Admins see all, students see only their department
    """
    user = request.current_user
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if user['role'] in ['Admin', 'PlacementOfficer']:
        # Admins see all students
        cursor.execute("""
            SELECT s.*, d.DeptName 
            FROM Student s
            LEFT JOIN Department d ON s.DeptID = d.DeptID
            ORDER BY s.CGPA DESC
        """)
    else:
        # Students see only their department peers
        cursor.execute("""
            SELECT s.*, d.DeptName 
            FROM Student s
            LEFT JOIN Department d ON s.DeptID = d.DeptID
            WHERE s.DeptID = (
                SELECT DeptID FROM Student WHERE UserID = ?
            )
            ORDER BY s.CGPA DESC
        """, (user['user_id'],))
    
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(students), 200

@students_bp.route('/<int:student_id>', methods=['GET'])
@require_auth
def get_student(student_id):
    """Get single student details"""
    user = request.current_user
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.*, d.DeptName 
        FROM Student s
        LEFT JOIN Department d ON s.DeptID = d.DeptID
        WHERE s.StudentID = ?
    """, (student_id,))
    
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return jsonify({'error': 'Student not found'}), 404
    
    student_dict = dict(student)
    
    # Get skills
    cursor.execute("""
        SELECT sk.SkillName, sk.Category, ss.ProficiencyLevel
        FROM StudentSkill ss
        JOIN Skill sk ON ss.SkillID = sk.SkillID
        WHERE ss.StudentID = ?
    """, (student_id,))
    
    student_dict['skills'] = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(student_dict), 200

@students_bp.route('/', methods=['POST'])
@require_auth
@require_role('Admin', 'PlacementOfficer')
def create_student():
    """Create new student (Admin only)"""
    user = request.current_user
    data = request.get_json()
    
    required = ['Name', 'Email', 'DeptID', 'CGPA', 'GraduationYear']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO Student (Name, Email, ContactNumber, DeptID, CGPA, GraduationYear, Age)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (data['Name'], data['Email'], data.get('ContactNumber'), 
              data['DeptID'], data['CGPA'], data['GraduationYear'], data.get('Age')))
        
        student_id = cursor.lastrowid
        conn.commit()
        
        log_data_modification(
            user['user_id'], user['username'], 'INSERT', 'Student', student_id, new_data=data
        )
        
        return jsonify({'message': 'Student created', 'student_id': student_id}), 201
    
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@students_bp.route('/<int:student_id>', methods=['PUT'])
@require_auth
def update_student(student_id):
    """Update student (Admin or own profile)"""
    user = request.current_user
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user can update this student
    cursor.execute("SELECT UserID FROM Student WHERE StudentID = ?", (student_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return jsonify({'error': 'Student not found'}), 404
    
    # Only admin or the student themselves can update
    if user['role'] not in ['Admin', 'PlacementOfficer'] and result['UserID'] != user['user_id']:
        conn.close()
        return jsonify({'error': 'Forbidden'}), 403
    
    # Build update query
    allowed_fields = ['Name', 'ContactNumber', 'CGPA', 'Age', 'Image']
    updates = []
    values = []
    
    for field in allowed_fields:
        if field in data:
            updates.append(f"{field} = ?")
            values.append(data[field])
    
    if not updates:
        conn.close()
        return jsonify({'error': 'No valid fields to update'}), 400
    
    values.append(student_id)
    query = f"UPDATE Student SET {', '.join(updates)} WHERE StudentID = ?"
    
    try:
        cursor.execute(query, values)
        conn.commit()
        
        log_data_modification(
            user['user_id'], user['username'], 'UPDATE', 'Student', student_id, new_data=data
        )
        
        return jsonify({'message': 'Student updated'}), 200
    
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@students_bp.route('/<int:student_id>', methods=['DELETE'])
@require_auth
@require_role('Admin')
def delete_student(student_id):
    """Delete student (Admin only)"""
    user = request.current_user
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM Student WHERE StudentID = ?", (student_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Student not found'}), 404
        
        conn.commit()
        
        log_data_modification(
            user['user_id'], user['username'], 'DELETE', 'Student', student_id
        )
        
        return jsonify({'message': 'Student deleted'}), 200
    
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@students_bp.route('/<int:student_id>/skills', methods=['POST'])
@require_auth
def add_student_skill(student_id):
    """Add skill to student"""
    user = request.current_user
    data = request.get_json()
    
    if 'skill_id' not in data:
        return jsonify({'error': 'Missing skill_id'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO StudentSkill (StudentID, SkillID, ProficiencyLevel)
            VALUES (?, ?, ?)
        """, (student_id, data['skill_id'], data.get('proficiency_level', 'Beginner')))
        
        conn.commit()
        
        log_data_modification(
            user['user_id'], user['username'], 'INSERT', 'StudentSkill', None, new_data=data
        )
        
        return jsonify({'message': 'Skill added'}), 201
    
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
