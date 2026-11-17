"""
app/services/hermes_agent.py

Hermes AI Agent Service with Deterministic Tool Calling.

HOW IT WORKS:
- Exposes two deterministic business tools:
    1. `lead_lookup(email: str)` -> Finds lead details by email.
    2. `lead_status_update(lead_id: int, status: str, notes: str = "")` -> Updates status.
- Tool Whitelist & Safety:
    - LLM output cannot invoke arbitrary OS commands or Python code.
    - Only tools explicitly in `TOOL_REGISTRY` can be executed.
    - Parameters are strictly validated.
- Audit Trail:
    - Every tool call attempt (success or failure) is logged into the `agent_logs` SQLite table.
- Ollama / Hermes Integration:
    - Prompts Hermes 3 with structured schema and grammar enforcement (format="json").
    - Parses tool decisions deterministically (`lead_lookup` or `lead_status_update`).
    - Executes the tool, logs the action into `agent_logs`, and returns a clean, structured response.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.database import get_db_connection

logger = logging.getLogger(__name__)

# Valid lead statuses
VALID_STATUSES = {"new", "analyzing", "analyzed", "contacted", "closed"}

# ---------------------------------------------------------------------------
# Tool Implementations
# ---------------------------------------------------------------------------

async def tool_lead_lookup(email: str) -> Dict[str, Any]:
    """Find a lead by email address."""
    clean_email = email.strip().lower()
    async with get_db_connection() as db:
        cursor = await db.execute(
            """
            SELECT l.id, l.name, l.email, l.phone, l.company, l.message, l.status, l.created_at,
                   a.temperature, a.requirements, a.analysis_status
            FROM leads l
            LEFT JOIN lead_analysis a ON l.id = a.lead_id
            WHERE l.email = ?
            """,
            (clean_email,),
        )
        row = await cursor.fetchone()
        if not row:
            return {"found": False, "message": f"No lead found with email '{clean_email}'"}

        lead_data = dict(row)
        if lead_data.get("requirements"):
            try:
                lead_data["requirements"] = json.loads(lead_data["requirements"])
            except Exception:
                pass
        return {"found": True, "lead": lead_data}


async def tool_lead_status_update(lead_id: Any, status: str, notes: str = "") -> Dict[str, Any]:
    """Update a lead's status and record notes."""
    try:
        lead_id_int = int(lead_id)
    except (ValueError, TypeError):
        raise ValueError(f"lead_id must be an integer, got: {lead_id}")

    clean_status = status.strip().lower()
    if clean_status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{clean_status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}"
        )

    async with get_db_connection() as db:
        cursor = await db.execute("SELECT id, name, status FROM leads WHERE id = ?", (lead_id_int,))
        row = await cursor.fetchone()
        if not row:
            return {"updated": False, "message": f"Lead with id {lead_id_int} does not exist"}

        old_status = row["status"]
        await db.execute(
            "UPDATE leads SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (clean_status, lead_id_int),
        )
        await db.commit()

        return {
            "updated": True,
            "lead_id": lead_id_int,
            "old_status": old_status,
            "new_status": clean_status,
            "notes": notes,
        }


# Strict whitelist map
TOOL_REGISTRY = {
    "lead_lookup": tool_lead_lookup,
    "lead_status_update": tool_lead_status_update,
}


# ---------------------------------------------------------------------------
# Audit Logger
# ---------------------------------------------------------------------------

async def log_agent_action(
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_output: Any,
    success: bool,
    error_message: Optional[str] = None,
    lead_id: Optional[int] = None,
) -> None:
    """Record agent tool execution in agent_logs table."""
    try:
        async with get_db_connection() as db:
            await db.execute(
                """
                INSERT INTO agent_logs (lead_id, tool_name, tool_input, tool_output, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    lead_id,
                    tool_name,
                    json.dumps(tool_input) if tool_input else "{}",
                    json.dumps(tool_output) if isinstance(tool_output, (dict, list)) else str(tool_output),
                    1 if success else 0,
                    error_message,
                ),
            )
            await db.commit()
    except Exception as exc:
        logger.error("Failed to write to agent_logs: %s", exc)


# ---------------------------------------------------------------------------
# Agent Execution Core
# ---------------------------------------------------------------------------

AGENT_CHATML_PROMPT = """<|im_start|>system
You are an expert sales operations AI assistant that manages leads using tools.
CRITICAL INSTRUCTION:
- If the user query is NOT asking to search/lookup a specific lead or update a lead (for example: greetings, general questions about yourself, general talk, definitions), DO NOT call any tool! Set "tool": null, "arguments": {{}}, and provide your direct answer in "reply".
- Only call "lead_lookup" if an email address or specific lead lookup request is explicitly provided.
- Only call "lead_status_update" if a specific lead ID and status update is requested.

You MUST output ONLY a single valid JSON object with these exact keys:
- "tool": name of tool to call ("lead_lookup", "lead_status_update", or null)
- "arguments": dictionary of arguments to pass to the tool, or {{}}
- "reply": string response if no tool is required, or null

Available Tools:
- lead_lookup: Use whenever asked to find, check, inspect, or look up a lead by email address.
  Arguments: {{"email": "user@example.com"}}
- lead_status_update: Use whenever asked to update, change, mark, or close a lead by ID.
  Arguments: {{"lead_id": 123, "status": "new|analyzing|analyzed|contacted|closed", "notes": "optional notes"}}

Examples:
Query: "yo, can you check if alex@comp.io is in the db?"
Output: {{"tool": "lead_lookup", "arguments": {{"email": "alex@comp.io"}}, "reply": null}}

Query: "mark lead 4 as contacted, called them today"
Output: {{"tool": "lead_status_update", "arguments": {{"lead_id": 4, "status": "contacted", "notes": "called them today"}}, "reply": null}}

Query: "What is your main role as an assistant?"
Output: {{"tool": null, "arguments": {{}}, "reply": "I am an AI assistant designed to help manage, qualify, and update sales leads in the database."}}

Query: "what is the capital of France?"
Output: {{"tool": null, "arguments": {{}}, "reply": "The capital of France is Paris."}}
<|im_end|>
<|im_start|>user
{query}
<|im_end|>
<|im_start|>assistant
"""

async def execute_agent_query(query: str) -> Dict[str, Any]:
    """Process a natural language query with Hermes 3 and execute deterministic tools."""
    prompt = AGENT_CHATML_PROMPT.format(query=query)
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_response = data.get("response", "")
    except Exception as exc:
        logger.error("Error communicating with Ollama: %s", exc)
        return {
            "query": query,
            "tool_called": None,
            "tool_input": None,
            "result": None,
            "success": False,
            "error": f"LLM communication failure: {str(exc)}",
        }

    # Parse JSON from model
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                parsed = {"tool": None, "reply": raw_response}
        else:
            parsed = {"tool": None, "reply": raw_response}

    tool_name = parsed.get("tool")
    arguments = parsed.get("arguments") or {}
    reply = parsed.get("reply")

    # If no tool called, return direct reply
    if not tool_name or tool_name == "null":
        return {
            "query": query,
            "tool_called": None,
            "tool_input": None,
            "result": reply or "No action needed.",
            "success": True,
            "error": None,
        }

    # Tool Whitelist Enforcement
    if tool_name not in TOOL_REGISTRY:
        error_msg = f"Unauthorized or unknown tool: '{tool_name}'. Allowed: {list(TOOL_REGISTRY.keys())}"
        await log_agent_action(
            tool_name=tool_name,
            tool_input=arguments,
            tool_output=None,
            success=False,
            error_message=error_msg,
        )
        return {
            "query": query,
            "tool_called": tool_name,
            "tool_input": arguments,
            "result": None,
            "success": False,
            "error": error_msg,
        }

    # Execute deterministic tool
    tool_fn = TOOL_REGISTRY[tool_name]
    try:
        tool_result = await tool_fn(**arguments)
        lead_id = None
        if tool_name == "lead_status_update":
            lead_id = arguments.get("lead_id")
        elif tool_name == "lead_lookup" and tool_result.get("found"):
            lead_id = tool_result.get("lead", {}).get("id")

        await log_agent_action(
            tool_name=tool_name,
            tool_input=arguments,
            tool_output=tool_result,
            success=True,
            lead_id=lead_id,
        )

        return {
            "query": query,
            "tool_called": tool_name,
            "tool_input": arguments,
            "result": tool_result,
            "success": True,
            "error": None,
        }
    except Exception as exc:
        error_msg = f"Tool execution error: {str(exc)}"
        await log_agent_action(
            tool_name=tool_name,
            tool_input=arguments,
            tool_output=None,
            success=False,
            error_message=error_msg,
        )
        return {
            "query": query,
            "tool_called": tool_name,
            "tool_input": arguments,
            "result": None,
            "success": False,
            "error": error_msg,
        }
