"""
Module B — Mock Server (CareerTrack Schema)
CS 432, IIT Gandhinagar, Assignment 3

Simulates the CareerTrack Flask backend with:
  - Students, JobPostings, Applications tables (in-memory)
  - Session auth endpoint mirroring the real /api/auth/login
  - Multi-table transactions with a threading.Lock (Serializable isolation)
  - Failure injection and consistency verification debug endpoints
  - WAL checkpoint simulation

Use this when the real Flask backend is not yet running.

Run with:  python mock_server.py
Then run:  python benchmark_runner.py
"""

from flask import Flask, jsonify, request
import threading
import random
import time

app = Flask(__name__)
db_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────
# In-memory "database" — mirrors CareerTrack schema
# ─────────────────────────────────────────────────────────────────
students = {
    i: {
        "StudentID": i,
        "Name":      f"Student{i}",
        "Email":     f"student{i}@iitgn.ac.in",
        "CGPA":      round(6.0 + (i % 40) * 0.1, 2),
        "IsPlaced":  0,
        "DeptID":    (i % 5) + 1,
        "GraduationYear": 2026,
        "UserID":    i + 100,
    }
    for i in range(1, 101)
}

jobs = {
    i: {
        "JobID":       i,
        "CompanyID":   (i % 10) + 1,
        "CompanyName": f"Company{(i % 10) + 1}",
        "RoleTitle":   random.choice(["SDE", "Data Analyst", "ML Engineer", "DevOps"]),
        "MinCGPA":     round(6.0 + (i % 5) * 0.5, 1),
        "Package_LPA": round(10 + i * 0.5, 1),
        "Deadline":    None,
    }
    for i in range(1, 21)
}

applications = {}   # AppID → {AppID, StudentID, JobID, Status, ApplyDate}
_app_seq = [0]

# Failure injection state
_inject_point = [None]

# Simple session store
_sessions = {}
_admin_token = "mock-admin-token-123"
_sessions[_admin_token] = {"user_id": 0, "username": "admin", "role": "Admin"}


# ─────────────────────────────────────────────────────────────────
# Auth helper
# ─────────────────────────────────────────────────────────────────
def _get_session():
    """Extract and validate session token from request headers."""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip()
    return _sessions.get(token)


# ─────────────────────────────────────────────────────────────────
# Auth endpoints  (mirrors /api/auth/)
# ─────────────────────────────────────────────────────────────────
@app.post("/api/auth/login")
def login():
    data     = request.json or {}
    username = data.get("username", "")
    password = data.get("password", "")
    if username == "admin" and password == "admin123":
        return jsonify({
            "message":       "Login successful",
            "session_token": _admin_token,
            "username":      "admin",
            "role":          "Admin",
            "user_id":       0,
        })
    return jsonify({"error": "Invalid credentials"}), 401


# ─────────────────────────────────────────────────────────────────
# Students endpoints  (mirrors /api/students/)
# ─────────────────────────────────────────────────────────────────
@app.get("/api/students/")
def list_students():
    with db_lock:
        return jsonify(list(students.values()))


@app.get("/api/students/<int:sid>")
def get_student(sid):
    s = students.get(sid)
    if not s:
        return jsonify({"error": "Student not found"}), 404
    return jsonify(s)


@app.post("/api/students/")
def create_student():
    data = request.json or {}
    with db_lock:
        if _inject_point[0] == "before_commit":
            return jsonify({"error": "simulated crash before commit", "status": "rolled_back"}), 500
        sid = max(students.keys(), default=0) + 1
        cgpa = data.get("CGPA", 7.0)
        if not (0 <= float(cgpa) <= 10):
            return jsonify({"error": "CGPA must be in [0, 10]"}), 400
        students[sid] = {
            "StudentID": sid, "Name": data.get("Name", f"Student{sid}"),
            "Email": data.get("Email", f"s{sid}@iitgn.ac.in"),
            "CGPA": cgpa, "IsPlaced": 0,
            "DeptID": data.get("DeptID", 1),
            "GraduationYear": data.get("GraduationYear", 2026),
            "UserID": sid + 100,
        }
    return jsonify({"message": "Student created", "student_id": sid}), 201


@app.put("/api/students/<int:sid>")
def update_student(sid):
    data = request.json or {}
    with db_lock:
        if sid not in students:
            return jsonify({"error": "Student not found"}), 404
        if _inject_point[0] == "before_commit":
            return jsonify({"error": "simulated crash"}), 500
        if "CGPA" in data:
            cgpa = float(data["CGPA"])
            if not (0 <= cgpa <= 10):
                return jsonify({"error": "CGPA must be in [0, 10]"}), 400
            students[sid]["CGPA"] = cgpa
        if "IsPlaced" in data:
            students[sid]["IsPlaced"] = data["IsPlaced"]
        if "Name" in data:
            students[sid]["Name"] = data["Name"]
    return jsonify({"message": "Student updated"})


# ─────────────────────────────────────────────────────────────────
# Jobs endpoints  (mirrors /api/jobs/)
# ─────────────────────────────────────────────────────────────────
@app.get("/api/jobs/")
def list_jobs():
    with db_lock:
        return jsonify(list(jobs.values()))


@app.get("/api/jobs/<int:jid>")
def get_job(jid):
    j = jobs.get(jid)
    if not j:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(j)


# ─────────────────────────────────────────────────────────────────
# Applications endpoints  (mirrors /api/applications/)
# ─────────────────────────────────────────────────────────────────
@app.get("/api/applications/")
def list_applications():
    with db_lock:
        return jsonify(list(applications.values()))


@app.get("/api/applications/<int:aid>")
def get_application(aid):
    a = applications.get(aid)
    if not a:
        return jsonify({"error": "Application not found"}), 404
    return jsonify(a)


@app.get("/api/applications/job/<int:jid>")
def get_applications_for_job(jid):
    with db_lock:
        result = [a for a in applications.values() if a["JobID"] == jid]
    return jsonify(result)


@app.post("/api/applications/")
def apply_for_job():
    """
    Multi-table transaction:
      1. Verify student exists (FK check)
      2. Verify job exists (FK check)
      3. Check student CGPA >= job MinCGPA
      4. Check no duplicate application (PK / unique check)
      5. Insert application — atomically under db_lock
    """
    # Session: in mock server accept any session or the admin token
    data   = request.json or {}
    job_id = data.get("job_id") or data.get("JobID")

    if not job_id:
        return jsonify({"error": "Missing job_id"}), 400

    # Determine student from session (mock: use admin student_id=1 if not provided)
    session = _get_session()
    student_id = data.get("student_id") or data.get("StudentID") or 1

    with db_lock:
        # ── Failure injection ──────────────────────────────────
        if _inject_point[0] == "before_commit":
            return jsonify({"error": "simulated crash before commit",
                            "status": "rolled_back"}), 500
        if _inject_point[0] == "after_first_write":
            # Simulate partial write that gets rolled back
            return jsonify({"error": "simulated mid-transaction crash",
                            "status": "rolled_back"}), 500
        # ──────────────────────────────────────────────────────

        # FK check: student must exist
        student = students.get(int(student_id))
        if not student:
            return jsonify({"error": f"Student {student_id} not found", "status": "rolled_back"}), 404

        # FK check: job must exist
        job = jobs.get(int(job_id))
        if not job:
            return jsonify({"error": f"Job {job_id} not found", "status": "rolled_back"}), 404

        # Domain check: CGPA eligibility
        if student["CGPA"] < job["MinCGPA"]:
            return jsonify({
                "error": f"CGPA {student['CGPA']} below minimum {job['MinCGPA']}",
                "status": "rolled_back",
            }), 400

        # Duplicate application check
        for a in applications.values():
            if a["StudentID"] == int(student_id) and a["JobID"] == int(job_id):
                return jsonify({"error": "Already applied", "status": "rolled_back"}), 400

        # ── COMMIT: insert application ─────────────────────────
        _app_seq[0] += 1
        aid = _app_seq[0]
        applications[aid] = {
            "AppID":     aid,
            "StudentID": int(student_id),
            "JobID":     int(job_id),
            "Status":    "Applied",
            "ApplyDate": "2026-06-27",
        }

    return jsonify({"message": "Application submitted", "app_id": aid, "status": "committed"}), 201


@app.put("/api/applications/<int:aid>/status")
def update_application_status(aid):
    data   = request.json or {}
    status = data.get("status")
    valid  = {"Applied", "Shortlisted", "Selected", "Rejected", "Withdrawn"}
    if status not in valid:
        return jsonify({"error": f"Invalid status. Must be one of: {valid}"}), 400
    with db_lock:
        if aid not in applications:
            return jsonify({"error": "Application not found"}), 404
        applications[aid]["Status"] = status
    return jsonify({"message": "Status updated"})


# ─────────────────────────────────────────────────────────────────
# Analytics endpoint  (mirrors /api/analytics/placement-stats)
# ─────────────────────────────────────────────────────────────────
@app.get("/api/analytics/placement-stats")
def placement_stats():
    with db_lock:
        total   = len(students)
        placed  = sum(1 for s in students.values() if s["IsPlaced"])
        pct     = round(placed / total * 100, 2) if total else 0
        total_a = len(applications)
    return jsonify({
        "total_students":       total,
        "placed_students":      placed,
        "placement_percentage": pct,
        "total_applications":   total_a,
    })


# ─────────────────────────────────────────────────────────────────
# Debug endpoints
# ─────────────────────────────────────────────────────────────────
@app.post("/debug/inject_failure")
def inject_failure():
    body = request.json or {}
    _inject_point[0] = body.get("point")   # "before_commit" | "after_first_write" | None
    return jsonify({"injected": _inject_point[0]})


@app.post("/debug/checkpoint")
def checkpoint():
    """Simulate WAL flush / restart — clear injection state."""
    _inject_point[0] = None
    return jsonify({"status": "checkpointed"})


@app.get("/debug/verify_consistency")
def verify_consistency():
    issues = []
    with db_lock:
        # Domain: all CGPAs in [0, 10]
        for s in students.values():
            if not (0 <= float(s.get("CGPA", 5)) <= 10):
                issues.append(f"Student {s['StudentID']} CGPA={s['CGPA']} out of domain")

        # FK: all applications reference existing students and jobs
        for a in applications.values():
            if a["StudentID"] not in students:
                issues.append(f"App {a['AppID']} → missing StudentID {a['StudentID']}")
            if a["JobID"] not in jobs:
                issues.append(f"App {a['AppID']} → missing JobID {a['JobID']}")

        # PK: no duplicate AppIDs (guaranteed by dict keys, but double-check)
        app_ids = list(applications.keys())
        if len(app_ids) != len(set(app_ids)):
            issues.append("Duplicate AppIDs detected!")

    if issues:
        return jsonify({"consistent": False, "details": issues})
    return jsonify({"consistent": True, "details": []})


@app.get("/debug/db_snapshot")
def db_snapshot():
    with db_lock:
        return jsonify({
            "student_count":     len(students),
            "job_count":         len(jobs),
            "application_count": len(applications),
        })


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("[Mock Server] CareerTrack Placement Management System")
    print("[Mock Server] Schema: Students / JobPostings / Applications")
    print("[Mock Server] Listening on http://localhost:5000")
    print("[Mock Server] Admin login: admin / admin123")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, threaded=True)
