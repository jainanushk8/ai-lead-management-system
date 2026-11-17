"""
scripts/test_api.py
Comprehensive test script for the Phase 2 REST API.

Runs 10 sequential tests against the running FastAPI server and reports
pass/fail for each. This script validates all CRUD operations, duplicate
detection, input validation, and error handling.
"""

import httpx
import sys
import json
import time

BASE_URL = "http://127.0.0.1:8000"
passed = 0
failed = 0


def report(test_name: str, success: bool, detail: str = ""):
    global passed, failed
    if success:
        passed += 1
        print(f"  [PASS] {test_name}")
    else:
        failed += 1
        print(f"  [FAIL] {test_name} -- {detail}")


def main():
    global passed, failed
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    ts = int(time.time())

    print("\n=== Phase 2 & 3 API Test Suite ===\n")

    # --- Test 1: Health Check ---
    try:
        r = client.get("/")
        report(
            "Health Check (GET /)",
            r.status_code == 200 and r.json()["status"] == "running",
            f"status={r.status_code} body={r.text}",
        )
    except Exception as e:
        report("Health Check (GET /)", False, str(e))

    # --- Test 2: Create Valid Lead ---
    lead_1 = {
        "name": "Rahul Sharma",
        "email": f"rahul_{ts}@techcorp.in",
        "phone": "+91 9876543210",
        "company": "TechCorp India",
        "message": "We need a custom CRM solution with AI-powered lead scoring.",
    }
    try:
        r = client.post("/api/leads", json=lead_1)
        data = r.json()
        report(
            "Create Valid Lead (POST /api/leads)",
            r.status_code == 201 and data.get("id") is not None,
            f"status={r.status_code} body={json.dumps(data, indent=2)}",
        )
        lead_1_id = data.get("id")
    except Exception as e:
        report("Create Valid Lead", False, str(e))
        lead_1_id = None

    # --- Test 3: Duplicate Lead (same email) ---
    try:
        r = client.post("/api/leads", json=lead_1)
        report(
            "Duplicate Detection (409 Conflict)",
            r.status_code == 409,
            f"status={r.status_code} body={r.text}",
        )
    except Exception as e:
        report("Duplicate Detection", False, str(e))

    # --- Test 4: Create Second Valid Lead ---
    lead_2 = {
        "name": "Priya Patel",
        "email": f"priya_{ts}@startupxyz.com",
        "phone": "9123456789",
        "company": "StartupXYZ",
        "message": "Looking for workflow automation tools to reduce manual data entry.",
    }
    try:
        r = client.post("/api/leads", json=lead_2)
        data = r.json()
        report(
            "Create Second Lead",
            r.status_code == 201 and data.get("id") is not None,
            f"status={r.status_code}",
        )
        lead_2_id = data.get("id")
    except Exception as e:
        report("Create Second Lead", False, str(e))
        lead_2_id = None

    # --- Test 5: List All Leads ---
    try:
        r = client.get("/api/leads")
        data = r.json()
        report(
            "List All Leads (GET /api/leads)",
            r.status_code == 200 and len(data) >= 2,
            f"status={r.status_code} count={len(data)}",
        )
    except Exception as e:
        report("List All Leads", False, str(e))

    # --- Test 6: Get Single Lead ---
    if lead_1_id:
        try:
            r = client.get(f"/api/leads/{lead_1_id}")
            data = r.json()
            report(
                f"Get Lead by ID (GET /api/leads/{lead_1_id})",
                r.status_code == 200 and data["email"] == lead_1["email"],
                f"status={r.status_code}",
            )
        except Exception as e:
            report("Get Lead by ID", False, str(e))

    # --- Test 7: Get Non-Existent Lead (404) ---
    try:
        r = client.get("/api/leads/999999")
        report(
            "Non-Existent Lead (404)",
            r.status_code == 404,
            f"status={r.status_code}",
        )
    except Exception as e:
        report("Non-Existent Lead (404)", False, str(e))

    # --- Test 8: Analyze Lead (Phase 3 Ollama Integration) ---
    if lead_1_id:
        try:
            r = client.post(f"/api/leads/{lead_1_id}/analyze", timeout=120.0)
            data = r.json()
            report(
                "Analyze Lead (Ollama AI classification)",
                r.status_code == 200 and data.get("analysis_status") == "completed",
                f"status={r.status_code} temperature={data.get('temperature')} requirements={data.get('requirements')}",
            )
        except Exception as e:
            report("Analyze Lead", False, str(e))

    # --- Test 9: Update Lead Status ---
    if lead_1_id:
        try:
            r = client.patch(
                f"/api/leads/{lead_1_id}",
                json={"status": "contacted"},
            )
            data = r.json()
            report(
                "Update Lead Status (PATCH)",
                r.status_code == 200 and data["status"] == "contacted",
                f"status={r.status_code} new_status={data.get('status')}",
            )
        except Exception as e:
            report("Update Lead Status", False, str(e))

    # --- Test 10: Validation Error (empty name) ---
    try:
        bad_lead = {
            "name": "   ",
            "email": "bad@test.com",
            "phone": "9876543210",
            "company": "Test Corp",
            "message": "Some message",
        }
        r = client.post("/api/leads", json=bad_lead)
        report(
            "Validation Error: Empty Name (422)",
            r.status_code == 422,
            f"status={r.status_code}",
        )
    except Exception as e:
        report("Validation Error: Empty Name", False, str(e))

    # --- Test 11: Validation Error (bad email) ---
    try:
        bad_lead = {
            "name": "Test User",
            "email": "not-an-email",
            "phone": "9876543210",
            "company": "Test Corp",
            "message": "Some message",
        }
        r = client.post("/api/leads", json=bad_lead)
        report(
            "Validation Error: Bad Email (422)",
            r.status_code == 422,
            f"status={r.status_code}",
        )
    except Exception as e:
        report("Validation Error: Bad Email", False, str(e))

    # --- Summary ---
    total = passed + failed
    print(f"\n=== Results: {passed}/{total} passed, {failed} failed ===\n")
    client.close()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
