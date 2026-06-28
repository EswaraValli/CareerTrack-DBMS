"""
Module B — Failure Simulation & Recovery Verifier
CS 432, IIT Gandhinagar, Assignment 3

Tests:
  - Crash before COMMIT → data must NOT persist
  - Crash after COMMIT  → data must persist (durability)
  - Mid-transaction crash → partial writes must roll back
  - Consistency check across all three tables after each failure
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:5000"

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

session = requests.Session()


def post(endpoint, payload=None):
    try:
        r = session.post(f"{BASE_URL}{endpoint}", json=payload or {}, timeout=10)
        return r.status_code, r.json() if r.content else {}
    except Exception as e:
        return 0, {"error": str(e)}


def get(endpoint):
    try:
        r = session.get(f"{BASE_URL}{endpoint}", timeout=10)
        return r.status_code, r.json() if r.content else {}
    except Exception as e:
        return 0, {"error": str(e)}


# ---------------------------------------------------------------------------
# Helper: read all three tables for a given user/product/order
# ---------------------------------------------------------------------------
def snapshot(user_id, product_id, order_id=None):
    _, user    = get(f"/users/{user_id}")
    _, product = get(f"/products/{product_id}")
    order = {}
    if order_id:
        _, order = get(f"/orders/{order_id}")
    return user, product, order


# ---------------------------------------------------------------------------
# Test 1: Crash BEFORE commit — nothing should be saved
# ---------------------------------------------------------------------------
def test_crash_before_commit():
    print("\n" + "-"*50)
    print("TEST 1: Crash before COMMIT — rollback expected")
    print("-"*50)

    # Snapshot before
    user_before, product_before, _ = snapshot(1, 1)
    balance_before = user_before.get("balance")
    stock_before   = product_before.get("stock")

    # Inject crash before commit
    status, body = post("/debug/inject_failure", {
        "point": "before_commit",
        "user_id": 1,
        "product_id": 1,
        "quantity": 1,
        "amount": 10.0,
    })
    print(f"  Inject response: HTTP {status} — {body}")

    time.sleep(0.5)

    # Snapshot after
    user_after, product_after, _ = snapshot(1, 1)
    balance_after = user_after.get("balance")
    stock_after   = product_after.get("stock")

    result = PASS if (balance_before == balance_after and stock_before == stock_after) else FAIL
    print(f"  Balance: {balance_before} → {balance_after}   {result}")
    print(f"  Stock  : {stock_before}   → {stock_after}     {result}")
    return result == PASS


# ---------------------------------------------------------------------------
# Test 2: Crash AFTER commit — data must persist
# ---------------------------------------------------------------------------
def test_crash_after_commit():
    print("\n" + "-"*50)
    print("TEST 2: Crash AFTER COMMIT — durability expected")
    print("-"*50)

    # Normal commit
    status, body = post("/transaction/place_order", {
        "user_id": 2,
        "product_id": 2,
        "quantity": 1,
        "amount": 15.0,
    })
    order_id = body.get("order_id")

    if status != 200:
        print(f"  {WARN} Could not commit test transaction (HTTP {status}): {body}")
        return None

    print(f"  Committed order_id={order_id}")

    # Simulate server restart / checkpoint flush
    post("/debug/checkpoint", {})
    time.sleep(1)

    # Verify data still present
    s2, order = get(f"/orders/{order_id}")
    if s2 == 200 and order.get("order_id") == order_id:
        print(f"  Order still present after checkpoint. {PASS}")
        return True
    else:
        print(f"  Order MISSING after checkpoint (HTTP {s2}). {FAIL}")
        return False


# ---------------------------------------------------------------------------
# Test 3: Mid-transaction crash — partial writes must roll back
# ---------------------------------------------------------------------------
def test_mid_transaction_crash():
    print("\n" + "-"*50)
    print("TEST 3: Mid-transaction crash — partial rollback")
    print("-"*50)

    user_before, product_before, _ = snapshot(3, 3)
    balance_before = user_before.get("balance")
    stock_before   = product_before.get("stock")

    # Inject crash after first write (Users updated, Products/Orders not yet)
    status, body = post("/debug/inject_failure", {
        "point": "after_first_write",
        "user_id": 3,
        "product_id": 3,
        "quantity": 1,
        "amount": 25.0,
    })
    print(f"  Inject response: HTTP {status} — {body}")
    time.sleep(0.5)

    user_after, product_after, _ = snapshot(3, 3)
    balance_after = user_after.get("balance")
    stock_after   = product_after.get("stock")

    balance_ok = (balance_before == balance_after)
    stock_ok   = (stock_before == stock_after)

    print(f"  Balance rolled back: {balance_before} → {balance_after}  {'✅' if balance_ok else '❌'}")
    print(f"  Stock   rolled back: {stock_before}   → {stock_after}    {'✅' if stock_ok else '❌'}")
    return balance_ok and stock_ok


# ---------------------------------------------------------------------------
# Test 4: Full consistency check across all tables
# ---------------------------------------------------------------------------
def test_consistency():
    print("\n" + "-"*50)
    print("TEST 4: Full consistency check")
    print("-"*50)

    status, body = get("/debug/verify_consistency")
    if status == 200:
        consistent = body.get("consistent", False)
        details    = body.get("details", "")
        if consistent:
            print(f"  All tables consistent. {PASS}")
        else:
            print(f"  Inconsistency: {details}  {FAIL}")
        return consistent
    else:
        print(f"  {WARN} verify_consistency endpoint returned HTTP {status}")
        return None


# ---------------------------------------------------------------------------
# Test 5: Rapid fire rollbacks — verify no dirty data accumulates
# ---------------------------------------------------------------------------
def test_repeated_rollbacks(n=20):
    print("\n" + "-"*50)
    print(f"TEST 5: {n} repeated bad transactions — all must roll back")
    print("-"*50)

    committed_accidentally = 0
    for i in range(n):
        status, body = post("/transaction/place_order", {
            "user_id":    i + 1,
            "product_id": (i % 20) + 1,
            "quantity":   -1,     # invalid
            "amount":     -500.0, # invalid
        })
        if status == 200:
            committed_accidentally += 1

    if committed_accidentally == 0:
        print(f"  0/{n} bad transactions committed. {PASS}")
        return True
    else:
        print(f"  {committed_accidentally}/{n} bad transactions INCORRECTLY committed. {FAIL}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("="*55)
    print("Module B — Failure Simulation & Recovery Tests")
    print(f"Target: {BASE_URL}")
    print("="*55)

    tests = [
        ("Crash before commit",         test_crash_before_commit),
        ("Durability after commit",      test_crash_after_commit),
        ("Mid-transaction crash",        test_mid_transaction_crash),
        ("Consistency check",            test_consistency),
        ("Repeated rollbacks",           test_repeated_rollbacks),
    ]

    passed = 0
    for name, fn in tests:
        try:
            result = fn()
            if result is True:
                passed += 1
            elif result is None:
                print(f"  [{name}] SKIPPED (endpoint not available)")
        except Exception as e:
            print(f"  [{name}] ERROR: {e}")

    print("\n" + "="*55)
    print(f"Results: {passed}/{len(tests)} tests passed")
    print("="*55)

    sys.exit(0 if passed == len(tests) else 1)
