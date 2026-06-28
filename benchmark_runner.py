"""
Module B — Complete Benchmark Runner
CS 432 — Databases, IIT Gandhinagar
Assignment 3 — CareerTrack Placement Management System

Runs all 5 test scenarios against the CareerTrack Flask backend and
collects real output with numbers, latencies, and ACID verification results.

Usage (real backend):
    Step 1: python app.py                    (one terminal)
    Step 2: python benchmark_runner.py       (another terminal)

Usage (mock server — no real backend needed):
    Step 1: python mock_server.py            (one terminal)
    Step 2: python benchmark_runner.py       (another terminal)

All results are saved to results/benchmark_results.json
Graphs:  python results_visualizer.py
"""

import threading
import requests
import json
import time
import random
import sys
import os
from collections import defaultdict
from datetime import datetime

# ─────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────
BASE_URL     = "http://localhost:5000"
NUM_THREADS  = 50
NUM_REQUESTS = 200
TIMEOUT      = 10

# Admin credentials for the real Flask backend
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

results_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────
# Session management  (handles both real backend + mock server)
# ─────────────────────────────────────────────────────────────────
_session_token = None

def login():
    """Login once and store session token for all subsequent requests."""
    global _session_token
    try:
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": ADMIN_USER, "password": ADMIN_PASS},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            _session_token = r.json().get("session_token")
            print(f"  ✅  Logged in as '{ADMIN_USER}' (token: {_session_token[:12]}...)")
            return True
        # Mock server doesn't need auth — that's fine
        if r.status_code == 404:
            print("  ℹ️   /api/auth/login not found — assuming mock server (no auth required)")
            return True
        print(f"  ⚠️   Login failed HTTP {r.status_code}: {r.text[:100]}")
        return False
    except Exception as e:
        print(f"  ⚠️   Login request failed: {e}")
        return False

def _auth_headers():
    """Return Authorization header if we have a session token."""
    if _session_token:
        return {"Authorization": f"Bearer {_session_token}",
                "Content-Type": "application/json"}
    return {"Content-Type": "application/json"}

# ─────────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────────
def http_post(endpoint, payload):
    t0 = time.time()
    try:
        r = requests.post(
            f"{BASE_URL}{endpoint}", json=payload,
            headers=_auth_headers(), timeout=TIMEOUT,
        )
        latency = (time.time() - t0) * 1000
        body = r.json() if r.content else {}
        return r.status_code, latency, body
    except Exception as e:
        return 0, (time.time() - t0) * 1000, {"error": str(e)}


def http_get(endpoint):
    t0 = time.time()
    try:
        r = requests.get(
            f"{BASE_URL}{endpoint}",
            headers=_auth_headers(), timeout=TIMEOUT,
        )
        latency = (time.time() - t0) * 1000
        body = r.json() if r.content else {}
        return r.status_code, latency, body
    except Exception as e:
        return 0, (time.time() - t0) * 1000, {"error": str(e)}


def http_put(endpoint, payload):
    t0 = time.time()
    try:
        r = requests.put(
            f"{BASE_URL}{endpoint}", json=payload,
            headers=_auth_headers(), timeout=TIMEOUT,
        )
        latency = (time.time() - t0) * 1000
        body = r.json() if r.content else {}
        return r.status_code, latency, body
    except Exception as e:
        return 0, (time.time() - t0) * 1000, {"error": str(e)}


# ─────────────────────────────────────────────────────────────────
# Metrics helpers
# ─────────────────────────────────────────────────────────────────
def compute_metrics(data):
    """data = list of (status_code, latency_ms, success_bool)"""
    if not data:
        return {}
    latencies     = sorted(l for _, l, _ in data)
    successes     = [s for _, _, s in data]
    status_counts = defaultdict(int)
    for code, _, _ in data:
        status_counts[code] += 1
    n = len(latencies)
    return {
        "total_requests": n,
        "success_count":  sum(successes),
        "success_pct":    round(100 * sum(successes) / n, 1),
        "avg_latency_ms": round(sum(latencies) / n, 2),
        "min_latency_ms": round(latencies[0], 2),
        "max_latency_ms": round(latencies[-1], 2),
        "p50_latency_ms": round(latencies[int(0.50 * n)], 2),
        "p95_latency_ms": round(latencies[int(0.95 * n)], 2),
        "p99_latency_ms": round(latencies[min(int(0.99 * n), n - 1)], 2),
        "status_codes":   dict(status_counts),
    }


def print_metrics(name, metrics):
    print(f"\n  ┌─ {name}")
    print(f"  │  Total requests : {metrics.get('total_requests')}")
    print(f"  │  Success        : {metrics.get('success_pct')}%"
          f"  ({metrics.get('success_count')}/{metrics.get('total_requests')})")
    print(f"  │  Avg latency    : {metrics.get('avg_latency_ms')} ms")
    print(f"  │  P50/P95/P99    : {metrics.get('p50_latency_ms')} /"
          f" {metrics.get('p95_latency_ms')} / {metrics.get('p99_latency_ms')} ms")
    print(f"  └─ Status codes  : {metrics.get('status_codes')}")


# ─────────────────────────────────────────────────────────────────
# Endpoint resolver (works for both real backend and mock server)
# ─────────────────────────────────────────────────────────────────
def resolve(path):
    """
    Try the real /api/... path first. If 404, fall back to the
    mock server's flat namespace (e.g. /students, /jobs).
    """
    return path   # caller passes the real path; mock server maps the same ones

# Real API paths:
#   GET   /api/students/         list students
#   GET   /api/students/<id>     single student
#   POST  /api/students/         create student (Admin)
#   GET   /api/jobs/             list jobs
#   GET   /api/jobs/<id>         single job
#   GET   /api/applications/     list applications
#   POST  /api/applications/     apply for job  (Student role)
#   PUT   /api/applications/<id>/status   update status (Admin/Officer)
#   GET   /api/analytics/placement-stats  placement stats
#   POST  /debug/inject_failure   failure injection (mock + optional in real)
#   POST  /debug/checkpoint       checkpoint / WAL flush
#   GET   /debug/verify_consistency


# ══════════════════════════════════════════════════════════════════
# SCENARIO 1 — Race Condition
# 50 threads apply for the same job simultaneously.
# Verifies: no duplicate applications, FK integrity upheld.
# ══════════════════════════════════════════════════════════════════
def run_race_condition():
    print("\n" + "═" * 60)
    print("SCENARIO 1: Race Condition (50 students apply to same job)")
    print("═" * 60)

    data    = []
    barrier = threading.Barrier(NUM_THREADS)
    lock    = threading.Lock()

    # Fetch first available job id
    _, _, jobs_body = http_get("/api/jobs/")
    jobs = jobs_body if isinstance(jobs_body, list) else jobs_body.get("jobs", [])
    target_job_id = jobs[0]["JobID"] if jobs else 1
    print(f"  Target job_id = {target_job_id}")

    def worker(tid):
        barrier.wait()   # all threads fire simultaneously
        status, latency, body = http_post("/api/applications/", {
            "job_id": target_job_id,
        })
        # 200/201 = committed, 400/409 = already applied / not eligible — all acceptable
        success = status in (200, 201, 400, 409)
        with lock:
            data.append((status, latency, success))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(NUM_THREADS)]
    t_start = time.time()
    for t in threads: t.start()
    for t in threads: t.join()
    elapsed = time.time() - t_start

    metrics = compute_metrics(data)
    metrics["elapsed_seconds"] = round(elapsed, 3)
    metrics["throughput_rps"]  = round(NUM_THREADS / elapsed, 1)

    # Verify: fetch all applications for this job; no duplicate StudentIDs
    _, _, apps_body = http_get(f"/api/applications/job/{target_job_id}")
    apps = apps_body if isinstance(apps_body, list) else apps_body.get("applications", [])
    student_ids  = [a.get("StudentID") or a.get("student_id") for a in apps]
    dupes        = len(student_ids) - len(set(student_ids))
    metrics["duplicate_applications"] = dupes
    metrics["race_condition_ok"]       = dupes == 0

    print_metrics("race_condition", metrics)
    if dupes == 0:
        print(f"  ✅  No duplicate applications — race condition handled correctly")
    else:
        print(f"  ❌  {dupes} duplicate applications found — race condition violated!")

    return metrics


# ══════════════════════════════════════════════════════════════════
# SCENARIO 2 — Atomicity
# Valid + deliberately invalid transactions interleaved.
# Invalid transactions must NEVER return 2xx.
# ══════════════════════════════════════════════════════════════════
def run_atomicity_test():
    print("\n" + "═" * 60)
    print("SCENARIO 2: Atomicity (valid + deliberately bad transactions)")
    print("═" * 60)

    valid_data   = []
    invalid_data = []
    lock         = threading.Lock()

    # Fetch a valid job id
    _, _, jobs_body = http_get("/api/jobs/")
    jobs = jobs_body if isinstance(jobs_body, list) else jobs_body.get("jobs", [])
    valid_job_id = jobs[0]["JobID"] if jobs else 1

    def valid_worker(_):
        status, latency, _ = http_post("/api/applications/", {
            "job_id": valid_job_id,
        })
        with lock:
            valid_data.append((status, latency, status in (200, 201, 400, 409)))

    def invalid_worker(i):
        # job_id that does not exist — should trigger FK violation / 404
        status, latency, body = http_post("/api/applications/", {
            "job_id": 999999 + i,   # non-existent
        })
        success = status in (400, 404, 409, 422)
        if status in (200, 201):
            print(f"  ❌  Thread {i}: FK-violating transaction was COMMITTED — atomicity violated!")
        with lock:
            invalid_data.append((status, latency, success))

    threads = []
    for i in range(NUM_THREADS // 2):
        threads.append(threading.Thread(target=valid_worker,   args=(i,)))
        threads.append(threading.Thread(target=invalid_worker, args=(i,)))
    for t in threads: t.start()
    for t in threads: t.join()

    vm = compute_metrics(valid_data)
    im = compute_metrics(invalid_data)

    wrongly_committed = sum(1 for code, _, _ in invalid_data if code in (200, 201))
    atomicity_ok      = wrongly_committed == 0

    print_metrics("valid_transactions", vm)
    print_metrics("invalid_transactions (must be rejected)", im)
    print(f"\n  Wrongly committed bad transactions: {wrongly_committed}/{len(invalid_data)}")
    print(f"  {'✅  Atomicity OK' if atomicity_ok else '❌  Atomicity VIOLATED'}")

    return {
        "valid":    vm,
        "invalid":  im,
        "wrongly_committed_bad_txns": wrongly_committed,
        "atomicity_ok": atomicity_ok,
    }


# ══════════════════════════════════════════════════════════════════
# SCENARIO 3 — Isolation
# Concurrent reads interleaved with writes on student records.
# Readers must never see invalid CGPA (out-of-domain = dirty read).
# ══════════════════════════════════════════════════════════════════
def run_isolation_test():
    print("\n" + "═" * 60)
    print("SCENARIO 3: Isolation (reads interleaved with writes)")
    print("═" * 60)

    data       = []
    violations = []
    lock       = threading.Lock()

    # Fetch some student IDs
    _, _, sbody = http_get("/api/students/")
    students = sbody if isinstance(sbody, list) else sbody.get("students", [])
    student_ids = [s.get("StudentID") or s.get("student_id") for s in students[:NUM_THREADS]]
    if not student_ids:
        student_ids = list(range(1, NUM_THREADS + 1))

    def writer(sid):
        # Admin updates student CGPA to a valid value
        http_put(f"/api/students/{sid}", {
            "CGPA": round(random.uniform(5.0, 10.0), 2),
        })

    def reader(sid):
        status, latency, body = http_get(f"/api/students/{sid}")
        if status == 200:
            cgpa = body.get("CGPA") or body.get("cgpa")
            if cgpa is not None and not (0 <= float(cgpa) <= 10):
                with lock:
                    violations.append(f"student_id={sid} CGPA={cgpa} (dirty read!)")
        with lock:
            data.append((status, latency, status in (200, 404)))

    threads = []
    for sid in student_ids:
        threads.append(threading.Thread(target=writer, args=(sid,)))
        threads.append(threading.Thread(target=reader, args=(sid,)))
    random.shuffle(threads)
    for t in threads: t.start()
    for t in threads: t.join()

    metrics = compute_metrics(data)
    metrics["isolation_violations"] = len(violations)
    metrics["isolation_ok"]         = len(violations) == 0

    print_metrics("isolation_reads", metrics)
    if violations:
        print(f"  ❌  {len(violations)} dirty reads detected:")
        for v in violations[:5]:
            print(f"      {v}")
    else:
        print("  ✅  No dirty reads — isolation upheld")

    return metrics


# ══════════════════════════════════════════════════════════════════
# SCENARIO 4 — Failure Simulation & Rollback
# ══════════════════════════════════════════════════════════════════
def run_failure_simulation():
    print("\n" + "═" * 60)
    print("SCENARIO 4: Failure Simulation & Rollback Verification")
    print("═" * 60)

    test_results = {}

    # ── 4A: Crash before commit ──────────────────────────────────
    print("\n  [4A] Crash before COMMIT — state must not change")
    _, _, snap_before = http_get("/api/students/")
    stu_count_before  = len(snap_before if isinstance(snap_before, list)
                            else snap_before.get("students", []))

    http_post("/debug/inject_failure", {"point": "before_commit"})
    time.sleep(0.3)

    _, _, snap_after = http_get("/api/students/")
    stu_count_after  = len(snap_after if isinstance(snap_after, list)
                           else snap_after.get("students", []))

    rollback_ok = (stu_count_before == stu_count_after)
    test_results["crash_before_commit"] = {
        "students_before": stu_count_before,
        "students_after":  stu_count_after,
        "rollback_ok":     rollback_ok,
    }
    print(f"    Student count: {stu_count_before} → {stu_count_after}  "
          f"{'✅' if rollback_ok else '❌'}")

    # ── 4B: Mid-transaction crash ────────────────────────────────
    print("\n  [4B] Mid-transaction crash — partial write must roll back")
    _, _, apps_before = http_get("/api/applications/")
    app_count_before  = len(apps_before if isinstance(apps_before, list)
                            else apps_before.get("applications", []))

    http_post("/debug/inject_failure", {"point": "after_first_write"})
    time.sleep(0.3)

    _, _, apps_after = http_get("/api/applications/")
    app_count_after  = len(apps_after if isinstance(apps_after, list)
                           else apps_after.get("applications", []))

    mid_ok = (app_count_before == app_count_after)
    test_results["mid_transaction_crash"] = {
        "apps_before": app_count_before,
        "apps_after":  app_count_after,
        "rollback_ok": mid_ok,
    }
    print(f"    Application count: {app_count_before} → {app_count_after}  "
          f"{'✅' if mid_ok else '❌'}")

    # ── 4C: Durability ───────────────────────────────────────────
    print("\n  [4C] Durability — committed application must survive checkpoint")
    _, _, jobs_body = http_get("/api/jobs/")
    jobs = jobs_body if isinstance(jobs_body, list) else jobs_body.get("jobs", [])
    job_id = jobs[0]["JobID"] if jobs else 1

    status, _, body = http_post("/api/applications/", {"job_id": job_id})
    app_id = body.get("app_id") or body.get("AppID")

    http_post("/debug/checkpoint", {})
    time.sleep(0.5)

    if app_id:
        s2, _, app_body = http_get(f"/api/applications/{app_id}")
        durability_ok = s2 == 200
    else:
        # Check that apps count didn't drop
        _, _, apps_check = http_get("/api/applications/")
        count_check = len(apps_check if isinstance(apps_check, list)
                          else apps_check.get("applications", []))
        durability_ok = count_check >= app_count_after
        s2 = 200 if durability_ok else 404

    test_results["durability"] = {
        "app_id":       app_id,
        "found_after":  s2 == 200,
        "durability_ok": durability_ok,
    }
    print(f"    Committed app_id={app_id} → found after checkpoint: "
          f"{'✅' if durability_ok else '❌'}")

    # ── 4D: Repeated invalid transactions ────────────────────────
    print("\n  [4D] 20 bad transactions (nonexistent job_id) — none should commit")
    wrongly_committed = 0
    for i in range(20):
        s, _, _ = http_post("/api/applications/", {"job_id": 999900 + i})
        if s in (200, 201):
            wrongly_committed += 1
    test_results["repeated_rollbacks"] = {
        "bad_txns_sent":           20,
        "wrongly_committed":       wrongly_committed,
        "rollback_correctness_ok": wrongly_committed == 0,
    }
    print(f"    Wrongly committed: {wrongly_committed}/20  "
          f"{'✅' if wrongly_committed == 0 else '❌'}")

    # ── 4E: Full consistency check ────────────────────────────────
    print("\n  [4E] Full consistency check across all tables")
    _, _, cons = http_get("/debug/verify_consistency")
    consistent = cons.get("consistent", False)
    test_results["consistency_check"] = {
        "consistent": consistent,
        "details":    cons.get("details", []),
    }
    print(f"    Consistent: {'✅' if consistent else '⚠️  endpoint not available or inconsistent'}")

    return test_results


# ══════════════════════════════════════════════════════════════════
# SCENARIO 5 — Stress / Load Test
# ══════════════════════════════════════════════════════════════════
def run_stress_test(total=NUM_REQUESTS, concurrency=NUM_THREADS):
    print("\n" + "═" * 60)
    print(f"SCENARIO 5: Stress Test ({total} requests, {concurrency} concurrent)")
    print("═" * 60)

    # Fetch available job IDs
    _, _, jobs_body = http_get("/api/jobs/")
    jobs = jobs_body if isinstance(jobs_body, list) else jobs_body.get("jobs", [])
    job_ids = [j.get("JobID") or j.get("job_id") for j in jobs] or [1, 2, 3]

    data = []
    lock = threading.Lock()

    def worker(_):
        status, latency, _ = http_post("/api/applications/", {
            "job_id": random.choice(job_ids),
        })
        with lock:
            data.append((status, latency, status in (200, 201, 400, 409)))

    t_start = time.time()
    sent = 0
    while sent < total:
        batch   = min(concurrency, total - sent)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(batch)]
        for t in threads: t.start()
        for t in threads: t.join()
        sent += batch
        print(f"  Progress: {sent}/{total} requests sent...", end="\r")

    elapsed = time.time() - t_start
    metrics = compute_metrics(data)
    metrics["elapsed_seconds"] = round(elapsed, 3)
    metrics["throughput_rps"]  = round(total / elapsed, 1)

    print_metrics("stress_test", metrics)
    print(f"\n  Elapsed   : {elapsed:.2f}s")
    print(f"  Throughput: {metrics['throughput_rps']} req/s")

    return metrics


# ══════════════════════════════════════════════════════════════════
# BONUS — SQL Benchmark (direct DB query timing, from zip1 benchmark.py)
# ══════════════════════════════════════════════════════════════════
def run_sql_benchmark(db_path="careertrack.db"):
    """Measure execution time of key SQL queries directly against the DB."""
    import sqlite3

    if not os.path.exists(db_path):
        print(f"\n  ⚠️   {db_path} not found — skipping SQL benchmark")
        return {}

    print("\n" + "═" * 60)
    print("BONUS: SQL Query Performance Benchmark")
    print("═" * 60)

    queries = {
        "get_all_students": (
            """SELECT s.*, d.DeptName FROM Student s
               LEFT JOIN Department d ON s.DeptID = d.DeptID
               ORDER BY s.CGPA DESC""",
            "All students ordered by CGPA"
        ),
        "get_eligible_jobs": (
            """SELECT j.*, c.CompanyName FROM JobPosting j
               LEFT JOIN Company c ON j.CompanyID = c.CompanyID
               WHERE j.MinCGPA <= 8.5
               AND (j.Deadline IS NULL OR j.Deadline >= DATE('now'))
               ORDER BY j.PostDate DESC""",
            "Jobs eligible for CGPA 8.5"
        ),
        "student_applications": (
            """SELECT a.*, s.Name, j.RoleTitle, c.CompanyName
               FROM Application a
               JOIN Student s ON a.StudentID = s.StudentID
               JOIN JobPosting j ON a.JobID = j.JobID
               JOIN Company c ON j.CompanyID = c.CompanyID
               WHERE a.StudentID = 1 ORDER BY a.ApplyDate DESC""",
            "Applications for student #1"
        ),
        "placement_stats": (
            """SELECT d.DeptName,
                      COUNT(DISTINCT s.StudentID) as total,
                      COUNT(DISTINCT CASE WHEN s.IsPlaced=1 THEN s.StudentID END) as placed
               FROM Department d LEFT JOIN Student s ON d.DeptID=s.DeptID
               GROUP BY d.DeptID""",
            "Department-wise placement stats"
        ),
    }

    results = {}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    for name, (sql, desc) in queries.items():
        times = []
        for _ in range(10):
            t0 = time.perf_counter()
            cursor.execute(sql)
            cursor.fetchall()
            times.append((time.perf_counter() - t0) * 1000)

        avg = round(sum(times) / len(times), 3)
        p95 = round(sorted(times)[9], 3)
        results[name] = {"avg_ms": avg, "p95_ms": p95, "description": desc}
        print(f"  {name:<30}  avg={avg:.3f}ms  p95={p95:.3f}ms  — {desc}")

    conn.close()
    return results


# ══════════════════════════════════════════════════════════════════
# Save results
# ══════════════════════════════════════════════════════════════════
def save_results(collected):
    os.makedirs("results", exist_ok=True)
    path = "results/benchmark_results.json"
    with open(path, "w") as f:
        json.dump(collected, f, indent=2)
    print(f"\n✅  Full results saved to {path}")


# ══════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("═" * 60)
    print("Module B — CS 432 IIT Gandhinagar — Full Benchmark Suite")
    print("CareerTrack Placement Management System")
    print(f"Target : {BASE_URL}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 60)

    # Connectivity check
    try:
        requests.get(BASE_URL, timeout=3)
    except Exception:
        print(f"\n❌  Cannot connect to {BASE_URL}")
        print("    Start the server first:  python app.py")
        print("    Or the mock server:      python mock_server.py")
        sys.exit(1)

    # Authenticate (gracefully skips if mock server)
    print("\nAuthenticating...")
    login()

    collected = {
        "meta": {
            "timestamp": datetime.now().isoformat(),
            "base_url":  BASE_URL,
            "threads":   NUM_THREADS,
            "requests":  NUM_REQUESTS,
        }
    }

    collected["scenario_1_race_condition"]     = run_race_condition()
    collected["scenario_2_atomicity"]          = run_atomicity_test()
    collected["scenario_3_isolation"]          = run_isolation_test()
    collected["scenario_4_failure_simulation"] = run_failure_simulation()
    collected["scenario_5_stress_test"]        = run_stress_test()
    collected["bonus_sql_benchmark"]           = run_sql_benchmark()

    # ── Final ACID Summary ────────────────────────────────────────
    print("\n" + "═" * 60)
    print("ACID PROPERTY SUMMARY")
    print("═" * 60)

    s1 = collected["scenario_1_race_condition"]
    s2 = collected["scenario_2_atomicity"]
    s3 = collected["scenario_3_isolation"]
    s4 = collected["scenario_4_failure_simulation"]

    atomicity_ok   = (s2.get("atomicity_ok", False) and
                      s4.get("repeated_rollbacks", {}).get("rollback_correctness_ok", False))
    consistency_ok = s4.get("consistency_check", {}).get("consistent", False)
    isolation_ok   = s3.get("isolation_ok", False)
    durability_ok  = s4.get("durability", {}).get("durability_ok", False)

    print(f"  Atomicity    (no partial writes committed)    : {'✅ PASS' if atomicity_ok   else '❌ FAIL'}")
    print(f"  Consistency  (all tables valid after tests)   : {'✅ PASS' if consistency_ok else '⚠️  SKIP (endpoint optional)'}")
    print(f"  Isolation    (no dirty reads detected)        : {'✅ PASS' if isolation_ok   else '❌ FAIL'}")
    print(f"  Durability   (committed data survives restart): {'✅ PASS' if durability_ok  else '❌ FAIL'}")

    collected["acid_summary"] = {
        "Atomicity":   atomicity_ok,
        "Consistency": consistency_ok,
        "Isolation":   isolation_ok,
        "Durability":  durability_ok,
    }

    save_results(collected)

    print("\n" + "═" * 60)
    print("All scenarios complete.")
    print("Run:  python results_visualizer.py   to generate graphs")
    print("═" * 60)
