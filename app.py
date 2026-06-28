"""
CareerTrack Placement Management System - Main Application
Flask Web Application with REST API and Web UI
"""

from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'careertrack_secret_key_2026_change_in_production'
app.config['JSON_SORT_KEYS'] = False

# Enable CORS for API access
CORS(app)

# Register all API routes
from routes import register_routes
register_routes(app)

# Web UI Routes
@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')

@app.route('/login')
def login_page():
    """Login page"""
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page (requires login)"""
    return render_template('dashboard.html')

@app.route('/members')
def members_page():
    """Member portfolio page"""
    return render_template('members.html')

@app.route('/jobs')
def jobs_page():
    """Jobs listing page"""
    return render_template('jobs.html')

@app.route('/applications')
def applications_page():
    """Applications page"""
    return render_template('applications.html')

@app.route('/admin')
def admin_page():
    """Admin panel page"""
    return render_template('admin.html')

@app.route('/analytics')
def analytics_page():
    """Analytics page"""
    return render_template('analytics.html')

# Static files
@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return {'error': 'Resource not found'}, 404

@app.errorhandler(500)
def internal_error(error):
    return {'error': 'Internal server error'}, 500

# Database initialization
def initialize_database():
    """Initialize database on first run"""
    from db import init_database, check_table_exists
    
    # Check if database needs initialization
    if not check_table_exists('Users'):
        print("\n🔧 First run detected - Initializing database...")
        init_database()
        print("✅ Database initialized successfully!\n")
    else:
        print("✅ Database already initialized\n")

# Application entry point
if __name__ == '__main__':
    print("=" * 70)
    print("🎓 CareerTrack Placement Management System".center(70))
    print("=" * 70)
    print()
    
    # Initialize database
    initialize_database()
    
    print("🚀 Starting Flask application...")
    print("📍 Access the application at: http://localhost:5000")
    print()
    print("Default Admin Credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print()
    print("Default Placement Officer Credentials:")
    print("  Username: officer")
    print("  Password: officer123")
    print()
    print("=" * 70)
    print()
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
