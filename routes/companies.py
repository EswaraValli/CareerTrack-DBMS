"""
Companies API Routes for CareerTrack PMS
"""

from flask import request, jsonify
from routes import companies_bp
from auth_utils import require_auth, require_role
from audit import log_data_modification
from db import get_db_connection

@companies_bp.route('/', methods=['GET'])
@require_auth
def get_all_companies():
    """Get all companies"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Company ORDER BY CompanyName")
    companies = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(companies), 200

@companies_bp.route('/<int:company_id>', methods=['GET'])
@require_auth
def get_company(company_id):
    """Get single company details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Company WHERE CompanyID = ?", (company_id,))
    company = cursor.fetchone()
    conn.close()
    
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    return jsonify(dict(company)), 200

@companies_bp.route('/', methods=['POST'])
@require_auth
@require_role('Admin', 'PlacementOfficer')
def create_company():
    """Create new company"""
    user = request.current_user
    data = request.get_json()
    
    required = ['CompanyName']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO Company (CompanyName, Website, Industry, Location)
            VALUES (?, ?, ?, ?)
        """, (data['CompanyName'], data.get('Website'), 
              data.get('Industry'), data.get('Location')))
        
        company_id = cursor.lastrowid
        conn.commit()
        
        log_data_modification(
            user['user_id'], user['username'], 'INSERT', 'Company', company_id, new_data=data
        )
        
        return jsonify({'message': 'Company created', 'company_id': company_id}), 201
    
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
