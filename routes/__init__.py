"""
Routes package for CareerTrack PMS API
Contains all API endpoint definitions organized by functionality
"""

from flask import Blueprint

# Create blueprints for different route groups
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
students_bp = Blueprint('students', __name__, url_prefix='/api/students')
companies_bp = Blueprint('companies', __name__, url_prefix='/api/companies')
jobs_bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')
applications_bp = Blueprint('applications', __name__, url_prefix='/api/applications')
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

def register_routes(app):
    """
    Register all blueprints with the Flask app
    
    Args:
        app: Flask application instance
    """
    from . import auth, students, companies, jobs, applications, admin, analytics
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(companies_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(analytics_bp)
