"""
Module B: High-Concurrency API Load Testing & Failure Simulation
CS 432 - Databases, IIT Gandhinagar
Assignment 3

This Locust file simulates concurrent users performing:
  - Multi-table transactions (Users, Orders, Products)
  - Race condition scenarios (e.g., concurrent stock deduction)
  - Failure injection and rollback verification
  - Stress testing with hundreds/thousands of requests
"""

import random
import json
import time
from locust import HttpUser, task, between, events
from locust.env import Environment

# ---------------------------------------------------------------------------
# Configuration — change BASE_URL in locust command or here
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:5000"   # your Flask/FastAPI server


class DatabaseUser(HttpUser):
    """
    Simulates a regular user performing read/write transactions.
    """
    wait_time = between(0.1, 1.0)   # think time between requests

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    def post(self, endpoint, payload, name=None):
        return self.client.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            name=name or endpoint,
            catch_response=True,
        )

    def get(self, endpoint, name=None):
        return self.client.get(endpoint, name=name or endpoint, catch_response=True)

    # -----------------------------------------------------------------------
    # Tasks
    # -----------------------------------------------------------------------

    @task(3)
    def place_order_transaction(self):
        """
        Multi-table transaction: deduct stock, insert order, update user balance.
        Tests ATOMICITY across 3 relations.
        """
        user_id  = random.randint(1, 50)
        product_id = random.randint(1, 20)
        quantity = random.randint(1, 3)
        amount   = round(random.uniform(10.0, 500.0), 2)

        payload = {
            "user_id":    user_id,
            "product_id": product_id,
            "quantity":   quantity,
            "amount":     amount,
        }

        with self.post("/transaction/place_order", payload, name="place_order") as resp:
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") not in ("committed", "ok"):
                    resp.failure(f"Unexpected response: {data}")
            elif resp.status_code == 409:
                # Expected: insufficient stock or balance
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(2)
    def read_user(self):
        """Read a user record — should never fail even under heavy writes."""
        user_id = random.randint(1, 50)
        with self.get(f"/users/{user_id}", name="read_user") as resp:
            if resp.status_code not in (200, 404):
                resp.failure(f"HTTP {resp.status_code}")
            else:
                resp.success()

    @task(2)
    def read_product(self):
        """Read a product record."""
        product_id = random.randint(1, 20)
        with self.get(f"/products/{product_id}", name="read_product") as resp:
            if resp.status_code not in (200, 404):
                resp.failure(f"HTTP {resp.status_code}")
            else:
                resp.success()

    @task(1)
    def update_user_balance(self):
        """Update user balance — isolated write."""
        user_id = random.randint(1, 50)
        delta   = round(random.uniform(-50.0, 200.0), 2)
        with self.post(
            f"/users/{user_id}/update_balance",
            {"delta": delta},
            name="update_balance",
        ) as resp:
            if resp.status_code in (200, 409):
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(1)
    def rollback_transaction(self):
        """
        Deliberately trigger a failing transaction to verify ROLLBACK.
        Sends invalid data so the server should roll back.
        """
        payload = {
            "user_id":    random.randint(1, 50),
            "product_id": random.randint(1, 20),
            "quantity":   -1,          # invalid — should cause rollback
            "amount":     -999.0,      # invalid
        }
        with self.post("/transaction/place_order", payload, name="rollback_test") as resp:
            # Expect 400 or 409 (rollback), NOT 200
            if resp.status_code in (400, 409, 422):
                resp.success()
            elif resp.status_code == 200:
                resp.failure("Expected rollback but got 200 — atomicity violated!")
            else:
                resp.failure(f"HTTP {resp.status_code}")


class RaceConditionUser(HttpUser):
    """
    Simulates many users hitting the same critical resource simultaneously
    to expose race conditions in stock/balance management.
    """
    wait_time = between(0.01, 0.1)   # very fast — stress the lock

    @task
    def race_book_last_item(self):
        """
        All users try to buy product_id=1 (limited stock).
        Only some should succeed; rest should get 409.
        No negative stock should result.
        """
        payload = {
            "user_id":    random.randint(1, 100),
            "product_id": 1,           # same product for all users
            "quantity":   1,
            "amount":     10.0,
        }
        with self.client.post(
            "/transaction/place_order",
            json=payload,
            name="race_condition",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 409, 400):
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")


class FailureInjectionUser(HttpUser):
    """
    Injects crashes/failures mid-transaction via special API endpoints
    (your server should expose these for testing).
    """
    wait_time = between(1, 3)

    @task(1)
    def inject_crash_before_commit(self):
        """
        Tells the server to crash after writes but before COMMIT.
        After restart the data must NOT be visible.
        """
        with self.client.post(
            "/debug/inject_failure",
            json={"point": "before_commit", "transaction_type": "place_order"},
            name="inject_crash_before_commit",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 500, 503):
                resp.success()  # crash is expected
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(1)
    def inject_crash_after_first_write(self):
        """
        Crash after updating Users but before updating Products/Orders.
        Tests partial-write rollback.
        """
        with self.client.post(
            "/debug/inject_failure",
            json={"point": "after_first_write", "transaction_type": "place_order"},
            name="inject_crash_mid_txn",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 500, 503):
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(1)
    def verify_consistency_after_crash(self):
        """Check all-table consistency via a dedicated endpoint."""
        with self.client.get(
            "/debug/verify_consistency",
            name="verify_consistency",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if data.get("consistent") is True:
                    resp.success()
                else:
                    resp.failure(f"Inconsistency detected: {data.get('details')}")
            else:
                resp.failure(f"HTTP {resp.status_code}")


# ---------------------------------------------------------------------------
# Event hooks — log summary stats to a JSON file
# ---------------------------------------------------------------------------
@events.quitting.add_listener
def on_quit(environment, **kwargs):
    stats = environment.stats
    summary = {
        "total_requests":  stats.total.num_requests,
        "total_failures":  stats.total.num_failures,
        "avg_response_ms": round(stats.total.avg_response_time, 2),
        "rps":             round(stats.total.current_rps, 2),
    }
    with open("results/locust_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("\n[Module B] Test summary written to results/locust_summary.json")
