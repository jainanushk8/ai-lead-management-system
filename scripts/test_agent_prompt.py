import httpx
prompt = """You are an AI assistant that manages leads using deterministic tools.
Available tools:
1. lead_lookup: Find a lead by email address.
   Arguments: {"email": "string"}
2. lead_status_update: Update lead status.
   Arguments: {"lead_id": integer, "status": "string (new|analyzing|analyzed|contacted|closed)", "notes": "string"}

Respond ONLY with a JSON object:
{"tool": "lead_lookup" or "lead_status_update" or null, "arguments": {...}, "reply": "optional message if no tool"}

User query: Please check if we have a lead for rahul@techcorp.in
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
print("RESP:", resp.json()["response"])
