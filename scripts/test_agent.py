"""
scripts/test_agent.py

Test script to verify Phase 4 Hermes AI Agent tool-calling capabilities:
1. lead_lookup via natural language
2. lead_status_update via natural language
3. direct conversational query without tools
4. audit logging verification in SQLite agent_logs table
"""

import httpx
import sqlite3
import json
import sys

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
    client = httpx.Client(base_url=BASE_URL, timeout=120.0)

    print("\n=== Phase 4 Hermes Agent Test Suite ===\n")

    # Test 1: Lead Lookup Tool Calling
    try:
        q1 = "Please check if we have a lead for rahul@techcorp.in and fetch their info"
        r = client.post("/api/agent/query", json={"query": q1})
        data = r.json()
        report(
            "Agent Tool Calling: lead_lookup",
            r.status_code == 200 and data.get("tool_called") == "lead_lookup" and data.get("success") is True,
            f"status={r.status_code} data={json.dumps(data, indent=2)}",
        )
    except Exception as e:
        report("Agent Tool Calling: lead_lookup", False, str(e))

    # Test 2: Lead Status Update Tool Calling
    try:
        q2 = "Update the status of lead with id 1 to contacted with notes 'Spoke with CTO today'"
        r = client.post("/api/agent/query", json={"query": q2})
        data = r.json()
        report(
            "Agent Tool Calling: lead_status_update",
            r.status_code == 200 and data.get("tool_called") == "lead_status_update" and data.get("success") is True,
            f"status={r.status_code} data={json.dumps(data, indent=2)}",
        )
    except Exception as e:
        report("Agent Tool Calling: lead_status_update", False, str(e))

    # Test 3: General Question (No Tool Calling)
    try:
        q3 = "What is your main role as an assistant?"
        r = client.post("/api/agent/query", json={"query": q3})
        data = r.json()
        report(
            "Agent Direct Answer (No Tool)",
            r.status_code == 200 and data.get("tool_called") is None and data.get("success") is True,
            f"status={r.status_code} data={json.dumps(data, indent=2)}",
        )
    except Exception as e:
        report("Agent Direct Answer", False, str(e))

    # Test 4: Verify agent_logs audit trail in SQLite
    try:
        conn = sqlite3.connect("leads.db")
        conn.row_factory = sqlite3.Row
        logs = conn.execute("SELECT * FROM agent_logs ORDER BY id DESC LIMIT 5").fetchall()
        report(
            "Audit Trail: agent_logs table has records",
            len(logs) >= 2,
            f"logs_count={len(logs)}",
        )
        for log in logs:
            print(f"    [LOG] id={log['id']} tool={log['tool_name']} success={log['success']} input={log['tool_input']}")
        conn.close()
    except Exception as e:
        report("Audit Trail: agent_logs", False, str(e))

    # Summary
    total = passed + failed
    print(f"\n=== Agent Test Results: {passed}/{total} passed, {failed} failed ===\n")
    client.close()
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
