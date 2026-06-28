"""
Module B — Custom Multi-Threaded Stress Test
CS 432, IIT Gandhinagar, Assignment 3

Run this script directly (no Locust needed):
    python custom_scripts/stress_test.py

It covers:
  1. Concurrent order placement (race condition on stock)
  2. Rollback verification (deliberate bad transactions)
  3. Consistency checks after failures
  4. Durability check (restart simulation)
"""

import threading
import requests
import json
import time
import random
import sys
from collections import defaultdict
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL     = "http://localhost:5000"
NUM_THREADS  = 50       # concurrent users
NUM_REQUESTS = 200      # total requests per scenario
TIMEOUT      = 10       # seconds per HTTP request

results_lock = threading.Lock()
results = defaultdict(list)  # scenario -> list of (status_code, latency_ms, ok)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def post(endpoint, payload):
    t0 = time.time()
    try:
        r = requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=TIMEOUT)
        latency = (time.time() - t0) * 1000
        return r.status_code, latency, r.json() if r.content else {}
    except Exception as e:
        latency = (time.time() - t0) * 1000
        return 0, latency, {"error": str(e)}


def get(endpoint):
    t0 = time.time()
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)
        latency = (time.time() - t0) * 1000
        return r.status_code, latency, r.json() if r.content else {}
    except Exception as e:
        latency = (time.time() - t0) * 1000
        return 0, latency, {"error": str(e)}


def record(scenario, status, latency, success):
    with results_lock:
        results[scenario].append((status, round(latency, 2), success))


# ---------------------------------------------------------------------------
# Scenario 1: Race Condition — all threads buy product_id=1 simultaneously
# ---------------------------------------------------------------------------
def race_condition_worker(thread_id, barrier):
    """All threads wait at barrier then fire simultaneously."""
    barrier.wait()
    payload = {
        "user_id":    thread_id + 1,
        "product_id": 1,
        "quantity":   1,
        "amount":     50.0,
    }
    status, latency, body = post("/transaction/place_order", payload)
    success = status in (200, 409)   # 409 = out of stock is fine
    record("race_condition", status, latency, success)


def run_race_condition_test():
    print("\n" + "="*60)
    print("SCENARIO 1: Race Condition (all threads buy same product)")
    print("="*60)

    barrier = threading.Barrier(NUM_THREADS)
    threads = [
        threading.Thread(target=race_condition_worker, args=(i, barrier))
        for i in range(NUM_THREADS)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    summarise("race_condition")

    # Verify stock never went negative
    status, _, body = get("/products/1")
    if status == 200:
        stock = body.get("stock", -1)
        if stock < 0:
            print(f"  ❌  RACE CONDITION DETECTED: stock = {stock} (negative!)")
        else:
            print(f"  ✅  Stock integrity OK: stock = {stock}")
    else:
        print(f"  ⚠️   Could not verify stock (HTTP {status})")


# ---------------------------------------------------------------------------
# Scenario 2: Atomicity — crash mid-transaction, verify rollback
# ---------------------------------------------------------------------------
def atomicity_worker(i):
    # Valid transaction
    payload = {
        "user_id":    random.randint(1, 50),
        "product_id": random.randint(1, 20),
        "quantity":   1,
        "amount":     round(random.uniform(10.0, 200.0), 2),
    }
    status, latency, body = post("/transaction/place_order", payload)
    success = status in (200, 409)
    record("atomicity_normal", status, latency, success)


def atomicity_bad_worker(i):
    # Invalid transaction — must rollback
    payload = {
        "user_id":    random.randint(1, 50),
        "product_id": random.randint(1, 20),
        "quantity":   -5,       # invalid
        "amount":     -9999.0,  # invalid
    }
    status, latency, body = post("/transaction/place_order", payload)
    # Should NOT return 200 (that would mean invalid data was committed)
    success = status in (400, 409, 422)
    if status == 200:
        print(f"  ❌  Thread {i}: BAD transaction was COMMITTED (atomicity violated)!")
    record("atomicity_rollback", status, latency, success)


def run_atomicity_test():
    print("\n" + "="*60)
    print("SCENARIO 2: Atomicity (valid + invalid transactions mixed)")
    print("="*60)

    threads = []
    for i in range(NUM_THREADS // 2):
        threads.append(threading.Thread(target=atomicity_worker, args=(i,)))
        threads.append(threading.Thread(target=atomicity_bad_worker, args=(i,)))
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    summarise("atomicity_normal")
    summarise("atomicity_rollback")


# ---------------------------------------------------------------------------
# Scenario 3: Isolation — interleaved reads during writes
# ---------------------------------------------------------------------------
_isolation_violations = []


def isolation_writer(user_id):
    payload = {
        "user_id":    user_id,
        "product_id": random.randint(1, 20),
        "quantity":   1,
        "amount":     10.0,
    }
    post("/transaction/place_order", payload)


def isolation_reader(user_id):
    """Read the user mid-write and check for partial state."""
    status, latency, body = get(f"/users/{user_id}")
    if status == 200:
        balance = body.get("balance", 0)
        if balance < 0:
            with results_lock:
                _isolation_violations.append(
                    f"user_id={user_id} balance={balance} (negative mid-write)"
                )
    record("isolation", status, latency, status in (200, 404))


def run_isolation_test():
    print("\n" + "="*60)
    print("SCENARIO 3: Isolation (concurrent reads and writes)")
    print("="*60)

    threads = []
    for i in range(1, NUM_THREADS + 1):
        threads.append(threading.Thread(target=isolation_writer, args=(i,)))
        threads.append(threading.Thread(target=isolation_reader, args=(i,)))

    random.shuffle(threads)   # interleave randomly
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    summarise("isolation")
    if _isolation_violations:
        print(f"  ❌  Isolation violations detected ({len(_isolation_violations)}):")
        for v in _isolation_violations[:5]:
            print(f"      {v}")
    else:
        print("  ✅  No isolation violations detected")


# ---------------------------------------------------------------------------
# Scenario 4: Durability — verify committed data survives simulated restart
# ---------------------------------------------------------------------------
def run_durability_test():
    print("\n" + "="*60)
    print("SCENARIO 4: Durability (data persists after restart)")
    print("="*60)

    # 1. Commit a known transaction
    payload = {
        "user_id":    999,
        "product_id": 1,
        "quantity":   1,
        "amount":     42.0,
    }
    status, _, body = post("/transaction/place_order", payload)
    order_id = body.get("order_id")

    if status not in (200, 409):
        print(f"  ⚠️   Could not place durability test order (HTTP {status})")
        return

    if status == 409:
        print("  ⚠️   Durability test order rejected (out of stock / balance) — skipping")
        return

    print(f"  Committed order_id={order_id}. Triggering server checkpoint...")

    # 2. Ask the server to checkpoint / simulate restart
    post("/debug/checkpoint", {})
    time.sleep(1)

    # 3. Verify the order still exists
    status2, _, body2 = get(f"/orders/{order_id}")
    if status2 == 200:
        print(f"  ✅  Durability OK: order_id={order_id} survived restart")
    elif status2 == 404:
        print(f"  ❌  DURABILITY VIOLATION: order_id={order_id} not found after restart!")
    else:
        print(f"  ⚠️   Unexpected status {status2} when checking durability")


# ---------------------------------------------------------------------------
# Scenario 5: Pure load test — N requests as fast as possible
# ---------------------------------------------------------------------------
def load_worker(_):
    payload = {
        "user_id":    random.randint(1, 50),
        "product_id": random.randint(1, 20),
        "quantity":   1,
        "amount":     round(random.uniform(5.0, 100.0), 2),
    }
    status, latency, _ = post("/transaction/place_order", payload)
    record("load_test", status, latency, status in (200, 409))


def run_load_test(total=NUM_REQUESTS, concurrency=NUM_THREADS):
    print("\n" + "="*60)
    print(f"SCENARIO 5: Load Test ({total} requests, {concurrency} threads)")
    print("="*60)

    batch_size = concurrency
    sent = 0
    t_start = time.time()

    while sent < total:
        batch = min(batch_size, total - sent)
        threads = [threading.Thread(target=load_worker, args=(i,)) for i in range(batch)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        sent += batch

    elapsed = time.time() - t_start
    summarise("load_test")
    print(f"  Total time: {elapsed:.2f}s  |  Throughput: {total/elapsed:.1f} req/s")


# ---------------------------------------------------------------------------
# Summary helper
# ---------------------------------------------------------------------------
def summarise(scenario):
    data = results[scenario]
    if not data:
        print(f"  [{scenario}] No data collected.")
        return

    latencies = [l for _, l, _ in data]
    successes = [s for _, _, s in data]
    status_counts = defaultdict(int)
    for code, _, _ in data:
        status_counts[code] += 1

    avg_lat = sum(latencies) / len(latencies)
    p95_lat = sorted(latencies)[int(0.95 * len(latencies))]
    success_pct = 100 * sum(successes) / len(successes)

    print(f"\n  [{scenario}]")
    print(f"    Requests   : {len(data)}")
    print(f"    Success    : {success_pct:.1f}%")
    print(f"    Avg latency: {avg_lat:.1f} ms")
    print(f"    P95 latency: {p95_lat:.1f} ms")
    print(f"    Status codes: {dict(status_counts)}")


# ---------------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------------
def save_results():
    output = {}
    for scenario, data in results.items():
        latencies = [l for _, l, _ in data]
        successes  = [s for _, _, s in data]
        status_counts = defaultdict(int)
        for code, _, _ in data:
            status_counts[code] += 1
        output[scenario] = {
            "total": len(data),
            "success_pct": round(100 * sum(successes) / max(len(successes), 1), 2),
            "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1), 2),
            "p95_latency_ms": round(sorted(latencies)[int(0.95 * max(len(latencies)-1, 0))], 2) if latencies else 0,
            "status_codes": dict(status_counts),
        }

    path = "results/stress_test_results.json"
    with open(path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n[Module B] Full results saved to {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("="*60)
    print("Module B — CS 432 IIT Gandhinagar — Stress Test Suite")
    print(f"Target: {BASE_URL}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    run_race_condition_test()
    run_atomicity_test()
    run_isolation_test()
    run_durability_test()
    run_load_test()

    save_results()

    print("\n" + "="*60)
    print("All scenarios complete. Check results/ directory.")
    print("="*60)
