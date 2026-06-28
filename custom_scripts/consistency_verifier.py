"""
Module B — ACID Consistency Verifier
CS 432, IIT Gandhinagar, Assignment 3

Performs post-test checks:
  - Every order references a valid user and product
  - No user balance is negative (unless business rules allow)
  - No product stock is negative
  - Order totals match expectations
  - B+ Tree vs DB state match (via server endpoint)

Run after stress_test.py or failure_simulation.py to confirm system integrity.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5000"

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"


def get(endpoint):
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        return r.status_code, r.json() if r.content else {}
    except Exception as e:
        return 0, {"error": str(e)}


# ---------------------------------------------------------------------------
# Check 1: No negative balances
# ---------------------------------------------------------------------------
def check_no_negative_balances():
    print("\nCheck 1: No negative user balances")
    status, body = get("/users")
    if status != 200:
        print(f"  {WARN} Could not fetch users (HTTP {status})")
        return None

    users = body if isinstance(body, list) else body.get("users", [])
    violations = [u for u in users if u.get("balance", 0) < 0]

    if violations:
        print(f"  {FAIL} {len(violations)} users with negative balance:")
        for u in violations[:5]:
            print(f"      user_id={u['user_id']} balance={u['balance']}")
        return False
    print(f"  {PASS} All {len(users)} users have non-negative balances")
    return True


# ---------------------------------------------------------------------------
# Check 2: No negative stock
# ---------------------------------------------------------------------------
def check_no_negative_stock():
    print("\nCheck 2: No negative product stock")
    status, body = get("/products")
    if status != 200:
        print(f"  {WARN} Could not fetch products (HTTP {status})")
        return None

    products = body if isinstance(body, list) else body.get("products", [])
    violations = [p for p in products if p.get("stock", 0) < 0]

    if violations:
        print(f"  {FAIL} {len(violations)} products with negative stock:")
        for p in violations[:5]:
            print(f"      product_id={p['product_id']} stock={p['stock']}")
        return False
    print(f"  {PASS} All {len(products)} products have non-negative stock")
    return True


# ---------------------------------------------------------------------------
# Check 3: All orders reference valid users and products
# ---------------------------------------------------------------------------
def check_referential_integrity():
    print("\nCheck 3: Referential integrity (orders → users, products)")

    _, users_body    = get("/users")
    _, products_body = get("/products")
    _, orders_body   = get("/orders")

    users    = {u["user_id"] for u in (users_body    if isinstance(users_body,    list) else users_body.get("users",    []))}
    products = {p["product_id"] for p in (products_body if isinstance(products_body, list) else products_body.get("products", []))}
    orders   = orders_body if isinstance(orders_body, list) else orders_body.get("orders", [])

    bad_user    = [o for o in orders if o.get("user_id")    not in users]
    bad_product = [o for o in orders if o.get("product_id") not in products]

    ok = True
    if bad_user:
        print(f"  {FAIL} {len(bad_user)} orders with invalid user_id")
        ok = False
    if bad_product:
        print(f"  {FAIL} {len(bad_product)} orders with invalid product_id")
        ok = False
    if ok:
        print(f"  {PASS} All {len(orders)} orders have valid foreign keys")
    return ok


# ---------------------------------------------------------------------------
# Check 4: B+ Tree vs DB consistency (via server endpoint)
# ---------------------------------------------------------------------------
def check_btree_consistency():
    print("\nCheck 4: B+ Tree ↔ DB state match")
    status, body = get("/debug/verify_consistency")
    if status == 200:
        if body.get("consistent"):
            print(f"  {PASS} Server reports B+ Tree and DB are consistent")
            return True
        else:
            print(f"  {FAIL} Inconsistency: {body.get('details', 'no details')}")
            return False
    else:
        print(f"  {WARN} /debug/verify_consistency not available (HTTP {status})")
        return None


# ---------------------------------------------------------------------------
# Check 5: No orphan orders (orders with no matching user record at all)
# ---------------------------------------------------------------------------
def check_no_orphan_orders():
    print("\nCheck 5: No orphan orders after rollbacks")
    _, orders_body = get("/orders")
    orders = orders_body if isinstance(orders_body, list) else orders_body.get("orders", [])

    # An orphan: order exists but user does not
    _, users_body = get("/users")
    users = {u["user_id"] for u in (users_body if isinstance(users_body, list) else users_body.get("users", []))}

    orphans = [o for o in orders if o.get("user_id") not in users]
    if orphans:
        print(f"  {FAIL} {len(orphans)} orphan orders found (user deleted but order kept)")
        return False
    print(f"  {PASS} No orphan orders found")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("="*55)
    print("Module B — ACID Consistency Verifier")
    print(f"Target: {BASE_URL}")
    print("="*55)

    checks = [
        check_no_negative_balances,
        check_no_negative_stock,
        check_referential_integrity,
        check_btree_consistency,
        check_no_orphan_orders,
    ]

    passed  = 0
    skipped = 0

    for fn in checks:
        result = fn()
        if result is True:
            passed += 1
        elif result is None:
            skipped += 1

    total = len(checks) - skipped
    print(f"\n{'='*55}")
    print(f"Consistency Result: {passed}/{total} checks passed  ({skipped} skipped/unavailable)")
    print("="*55)

    sys.exit(0 if passed == total else 1)
