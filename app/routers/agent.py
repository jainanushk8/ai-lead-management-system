"""
app/routers/agent.py
REST API endpoint for the Hermes AI Agent.

HOW IT WORKS:
- POST /api/agent/query accepts a natural-language query string.
- Phase 2: Returns a placeholder response indicating the agent service
  is not yet connected.
- Phase 4: This will route queries to the Hermes agent engine, which
  decides which tool to call (lead_lookup or lead_status_update), executes
  the tool, and returns the result.

INTERVIEW NOTES:
- The endpoint is defined early so that the n8n workflow can be designed
  against a known URL contract even before the agent logic is built.
- The response schema (AgentQueryResponse) is stable across phases.
"""

from fastapi import APIRouter

from app.models import AgentQueryRequest, AgentQueryResponse
from app.services.hermes_agent import execute_agent_query

router = APIRouter(prefix="/api/agent", tags=["Agent"])


@router.post(
    "/query",
    response_model=AgentQueryResponse,
    summary="Submit a query to the Hermes AI Agent",
)
async def agent_query(request: AgentQueryRequest):
    """
    Submit a natural-language instruction to the Hermes AI Agent.

    The Hermes agent decides whether to call `lead_lookup` or `lead_status_update`,
    enforces a deterministic tool whitelist, executes the tool, logs the action to
    agent_logs, and returns the structured result.
    """
    response_data = await execute_agent_query(request.query)
    return AgentQueryResponse(**response_data)
