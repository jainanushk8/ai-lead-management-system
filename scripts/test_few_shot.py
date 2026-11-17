import httpx
prompt = """<|im_start|>system
You are an expert sales operations AI. You manage leads strictly using deterministic tools.
You MUST output a single JSON object with these exact keys:
- "tool": name of tool to call ("lead_lookup", "lead_status_update", or null)
- "arguments": object with tool arguments, or {}
- "reply": string response if no tool is needed

Available Tools:
- lead_lookup: Use when asked to find, check, inspect, or look up a lead by email address.
  Arguments: {"email": "user@example.com"}
- lead_status_update: Use when asked to update, change, mark, or close a lead.
  Arguments: {"lead_id": 123, "status": "new|analyzing|analyzed|contacted|closed", "notes": "optional notes"}

Examples:
Query: "yo, can you check if alex@comp.io is in the db?"
Output: {"tool": "lead_lookup", "arguments": {"email": "alex@comp.io"}, "reply": null}

Query: "mark lead 4 as contacted, called them today"
Output: {"tool": "lead_status_update", "arguments": {"lead_id": 4, "status": "contacted", "notes": "called them today"}, "reply": null}

Query: "what is the capital of France?"
Output: {"tool": null, "arguments": {}, "reply": "Paris"}
<|im_end|>
<|im_start|>user
yo, can you check if mvance_1794899382@apexholdings.co is in the database and what they wanted?
<|im_end|>
<|im_start|>assistant
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
print("FEW-SHOT RESP:", resp.json()["response"])
