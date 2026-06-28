# 🎓 CareerTrack-DBMS

> **A Flask-based Placement Management System featuring Custom B+ Tree Indexing, ACID Transactions, Performance Benchmarking, and Database Sharding.**

<p align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?logo=bootstrap)
![REST API](https://img.shields.io/badge/API-REST-success)
![License](https://img.shields.io/badge/License-MIT-green)

</p>

---
## 📖 Project Overview

CareerTrack-DBMS is a modular **Placement Management System** developed as part of a multi-stage Database Management Systems project. Starting from relational database design, it evolved into a full-stack web application implementing advanced DBMS concepts such as **Custom B+ Tree Indexing, ACID Transactions, Write-Ahead Logging (WAL), Query Optimization, Concurrency Testing, and Hash-Based Database Sharding**.

The application provides secure role-based access for **Admins, Placement Officers, Students, and Companies**, enabling efficient placement management through REST APIs and an intuitive web interface.

---

## 🚀 Project Evolution

| Assignment | Major Deliverables |
|------------|--------------------|
| **Assignment 1** | ER Diagram, UML, SQL Schema Design |
| **Assignment 2A** | Custom B+ Tree, Benchmarking, Graph Visualization |
| **Assignment 2B** | Flask Web Application, REST APIs, RBAC, SQL Indexing |
| **Assignment 3A** | ACID Transactions, WAL, Crash Recovery |
| **Assignment 3B** | Concurrency Testing, Stress Testing, Load Testing |
| **Assignment 4** | Hash-Based Database Sharding |

---

## ✨ Key Features

- 👨‍🎓 Student, Company & Placement Management
- 🔐 Secure Authentication & Role-Based Access Control (RBAC)
- 🌐 RESTful APIs using Flask Blueprints
- 🌳 Custom B+ Tree Index Implementation
- ⚡ SQL Query Optimization with 45+ Indexes
- 🔄 ACID Transaction Processing with Write-Ahead Logging
- 🧪 Concurrency, Stress & Failure Testing
- 📊 Placement Analytics Dashboard
- 🗂️ Hash-Based Database Sharding
- 📝 Security Audit Logging

---

## 🛠️ Tech Stack

| Category | Technologies |
|----------|--------------|
| **Language** | Python |
| **Backend** | Flask |
| **Database** | SQLite |
| **Frontend** | HTML, CSS, Bootstrap 5, JavaScript |
| **Authentication** | Custom SQLite Session Tokens |
| **Testing** | Locust, Benchmark Scripts |
| **Visualization** | Graphviz, Matplotlib |
| **Version Control** | Git & GitHub |

---

## Project Structure

```
Module_B/
├── assets/
│   ├── diagrams/
│   └── screenshots/
├── app.py                        # Main Flask application
├── db.py                         # SQLite connection & schema init
├── audit.py                      # Audit logging (fixed: timedelta import)
├── auth_utils.py                 # Session management & password hashing
├── mock_server.py                # Standalone mock server (CareerTrack schema)
│
├── routes/
│   ├── __init__.py               # Blueprint registration
│   ├── auth.py                   # /api/auth/* — login, logout, register
│   ├── students.py               # /api/students/* — CRUD
│   ├── jobs.py                   # /api/jobs/* — job postings
│   ├── applications.py           # /api/applications/* — apply, status update
│   ├── companies.py              # /api/companies/*
│   ├── admin.py                  # /api/admin/* — users, audit logs
│   └── analytics.py             # /api/analytics/* — placement stats
│
├── sql/
│   ├── core_tables.sql           # Users, Sessions, AuditLog, SystemSettings
│   ├── project_dump.sql          # Student, Department, Company, JobPosting, Application...
│   └── indexes.sql               # Performance indexes for all tables
│
├── benchmark_runner.py           # ★ Main test script — all 5 ACID scenarios
├── sql_benchmark.py              # Direct SQL query timing (EXPLAIN QUERY PLAN)
├── results_visualizer.py         # Generates 5 charts from benchmark_results.json
│
├── custom_scripts/
│   ├── stress_test.py            # Multi-threaded stress test (standalone)
│   ├── failure_simulation.py     # Crash injection & recovery tests (standalone)
│   └── consistency_verifier.py  # Post-test table consistency sweep
│
├── locust_tests/
│   └── locustfile.py             # Locust load test (browser UI + stats)
│
├── results/                      # Auto-created output folder
│   ├── benchmark_results.json    # Full results from benchmark_runner.py
│   └── fig*.png                  # Charts from results_visualizer.py
│
├── templates/                    # HTML templates for Flask web UI
├── careertrack.db                # SQLite database (auto-created on first run)
└── requirements.txt
```

---

## ⚙️ Installation

```bash
git clone https://github.com/EswaraValli/CareerTrack-DBMS.git

cd CareerTrack-DBMS

pip install -r requirements.txt

python app.py
```

---

## 📸 Screenshots

> Screenshots and demo GIF will be added soon.

- Login Page
- Dashboard
- Student Management
- Analytics Dashboard
- Benchmark Results

---

## 🚀 Future Enhancements

- PostgreSQL Support
- Docker Deployment
- JWT Authentication
- CI/CD Pipeline
- Distributed Transactions
- Redis Caching
- Cloud Deployment

---
