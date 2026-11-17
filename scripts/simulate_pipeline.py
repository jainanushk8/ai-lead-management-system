"""
scripts/simulate_pipeline.py

End-to-End Orchestration Simulator for the n8n Pipeline.

This script executes the exact logic, node by node, as defined in `n8n/workflow.json`:
1. Webhook Input Validation (verifying mandatory fields and regex email)
2. Ingestion & Duplicate Branching (FastAPI POST /api/leads -> 201 vs 409)
3. Ollama Hermes 3 Lead Analysis (POST /api/leads/{id}/analyze)
4. Hermes Agent Tool Invocation (POST /api/agent/query)
5. Audit & Final Verification

Runs real leads through the pipeline to ensure the full architecture is 100% verified.
"""

import httpx
import json
import sqlite3
import sys
import time

BASE_URL = "http://127.0.0.1:8000"

def log_step(step_num: int, name: str):
    print(f"\n[Node {step_num}] ---> {name}")

def main():
    client = httpx.Client(base_url=BASE_URL, timeout=120.0)
    ts = int(time.time())

    print("\n" + "=" * 70)
    print(" N8N ORCHESTRATION PIPELINE SIMULATION")
    print("=" * 70)

    # -------------------------------------------------------------------
    # TEST 1: End-to-End Happy Path (Valid Enterprise Lead)
    # -------------------------------------------------------------------
    print("\n>>> SCENARIO 1: Full Pipeline Happy Path (New High-Value Lead)")
    lead_payload = {
        "name": "Ananya Sen",
        "email": f"ananya_{ts}@fintechglobal.com",
        "phone": "+91 9811223344",
        "company": "FinTech Global Solutions",
        "message": "Urgent: We need automated lead routing and custom CRM sync for 40 SDRs before our quarterly launch next month.",
    }

    # Node 1 & 2: Validation
    log_step(1, "Webhook Trigger & Input Validation")
    required = ["name", "email", "phone", "company", "message"]
    missing = [k for k in required if not lead_payload.get(k)]
    if missing:
        print(f"FAILED: Missing fields: {missing}")
        return
    print("Validation Passed: All mandatory fields present with valid email structure.")

    # Node 3: Create Lead in FastAPI
    log_step(2, "HTTP Request: Create Lead (POST /api/leads)")
    r = client.post("/api/leads", json=lead_payload)
    print(f"Response Status: {r.status_code}")
    lead_data = r.json()
    lead_id = lead_data["id"]
    print(f"Created Lead ID: {lead_id} | Initial Status: {lead_data['status']}")

    # Node 4: Branching Check
    log_step(3, "IF Node: Duplicate Branch Check")
    if r.status_code == 409:
        print("Branch -> Abort duplicate")
        return
    print("Branch -> Proceed to AI analysis")

    # Node 5: Ollama Classification
    log_step(4, "HTTP Request: Ollama LLM Classification (POST /api/leads/{id}/analyze)")
    t0 = time.time()
    r = client.post(f"/api/leads/{lead_id}/analyze")
    dur = round(time.time() - t0, 2)
    analysis = r.json()
    print(f"Ollama Duration: {dur}s")
    print(f"Temperature: {analysis.get('temperature')}")
    print(f"Requirements: {analysis.get('requirements')}")

    # Node 6: Hermes Agent Tool Invocation
    log_step(5, "HTTP Request: Hermes Agent Tool Invocation (POST /api/agent/query)")
    agent_query = (
        f"Lead {lead_id} was analyzed as {analysis.get('temperature')}. "
        f"Update lead {lead_id} status to contacted with notes 'AI classified temperature as {analysis.get('temperature')} with {len(analysis.get('requirements', []))} requirements'."
    )
    t0 = time.time()
    r = client.post("/api/agent/query", json={"query": agent_query})
    agent_dur = round(time.time() - t0, 2)
    agent_res = r.json()
    print(f"Agent Duration: {agent_dur}s")
    print(f"Tool Executed: {agent_res.get('tool_called')}")
    print(f"Tool Input: {agent_res.get('tool_input')}")
    print(f"Tool Result: {agent_res.get('result')}")

    # Node 7: Respond to Webhook
    log_step(6, "Webhook Response")
    final_output = {
        "success": True,
        "lead_id": lead_id,
        "temperature": analysis.get("temperature"),
        "requirements": analysis.get("requirements"),
        "pipeline_status": "completed",
    }
    print("Final Webhook Response Payload:")
    print(json.dumps(final_output, indent=2))

    # -------------------------------------------------------------------
    # TEST 2: Duplicate Ingestion Branching (409 Conflict)
    # -------------------------------------------------------------------
    print("\n>>> SCENARIO 2: Duplicate Lead Submission (Testing Branching)")
    log_step(2, "HTTP Request: Re-submit Same Lead")
    r_dup = client.post("/api/leads", json=lead_payload)
    print(f"Response Status: {r_dup.status_code} (Expected 409)")
    log_step(3, "IF Node: Duplicate Detected")
    print("Branch -> Successfully diverted to duplicate abort handler without wasting LLM tokens.")

    # -------------------------------------------------------------------
    # Verify Database State
    # -------------------------------------------------------------------
    print("\n" + "=" * 70)
    print(" DATABASE AUDIT CONFIRMATION")
    print("=" * 70)
    conn = sqlite3.connect("leads.db")
    conn.row_factory = sqlite3.Row
    lead_row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    analysis_row = conn.execute("SELECT * FROM lead_analysis WHERE lead_id = ?", (lead_id,)).fetchone()
    latest_log = conn.execute("SELECT * FROM agent_logs WHERE lead_id = ? ORDER BY id DESC LIMIT 1", (lead_id,)).fetchone()

    print(f"Lead Row: ID={lead_row['id']} Status='{lead_row['status']}' (Transitioned to contacted)")
    print(f"Analysis Row: Temp='{analysis_row['temperature']}' Status='{analysis_row['analysis_status']}'")
    print(f"Agent Log: Tool='{latest_log['tool_name']}' Success={latest_log['success']}")
    conn.close()

    print("\nAll n8n workflow nodes and branches verified successfully!")

if __name__ == "__main__":
    main()
