import httpx
prompt = """You are an AI Lead Operations Agent that manages sales leads using tools.
Available tools:
1. "lead_lookup": Find an existing lead by email address.
   Arguments format: {"email": "string"}
2. "lead_status_update": Update a lead's status in the database.
   Arguments format: {"lead_id": integer, "status": "new|analyzing|analyzed|contacted|closed", "notes": "string"}

Respond ONLY with a valid JSON object matching this structure:
{"tool": "lead_lookup" or "lead_status_update" or null, "arguments": {...}, "reply": "direct answer if no tool is required"}

User Query: yo, can you check if mvance_1794899382@apexholdings.co is in the database and what they wanted?
"""
resp = httpx.post(
    "http://127.0.0.1:11434/api/generate",
    json={
        "model": "hermes3:3b",
        "prompt": prompt,
        "format": "json",
        "stream": False
    },
    timeout=60.0
)
print("STATUS:", resp.status_code)
print("RAW RESP:", resp.json()["response"])
