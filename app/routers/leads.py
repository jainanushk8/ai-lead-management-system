"""
app/routers/leads.py
REST API endpoints for lead management (CRUD + analysis trigger).

HOW IT WORKS:
- POST /api/leads: Validates incoming JSON via LeadCreate Pydantic schema,
  then attempts an INSERT into the leads table. If the email already exists,
  SQLite raises an IntegrityError (because of the UNIQUE constraint on email),
  which we catch and return as a 409 Conflict response. This is the primary
  duplicate prevention mechanism.

- GET /api/leads: Returns all leads from the database. In production, this
  would include pagination parameters; for the assessment scope, returning
  all records is acceptable.

- GET /api/leads/{lead_id}: Returns a single lead by its integer ID. If the
  ID does not exist, returns 404.

- POST /api/leads/{lead_id}/analyze: Triggers Ollama-based classification.
  In Phase 2, this endpoint exists as a placeholder that returns a "pending"
  status. Phase 3 will connect the actual Ollama service.

- PATCH /api/leads/{lead_id}: Updates the status field of an existing lead.
  Used by the n8n workflow and the Hermes agent to transition leads through
  their lifecycle (new -> analyzed -> contacted -> closed).

INTERVIEW NOTES:
- Duplicate detection uses the database constraint (UNIQUE on email) rather
  than a pre-query SELECT. This is an atomic operation: even if two identical
  requests arrive simultaneously, the database engine serializes the INSERTs
  and the second one fails cleanly. A SELECT-then-INSERT approach would have
  a race condition window.
- All database operations use async with get_db_connection() to avoid blocking
  the FastAPI event loop.
- HTTP status codes follow REST conventions: 201 Created, 409 Conflict,
  404 Not Found, 422 Unprocessable Entity (Pydantic validation failures).
"""

import json
import sqlite3

from fastapi import APIRouter, HTTPException, status

from app.database import get_db_connection
from app.models import LeadCreate, LeadResponse, LeadAnalysisResponse

router = APIRouter(prefix="/api/leads", tags=["Leads"])


@router.post(
    "",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new lead",
    responses={
        409: {"description": "Lead with this email already exists"},
        422: {"description": "Validation error in request body"},
    },
)
async def create_lead(lead: LeadCreate):
    """
    Receive a new lead, validate it, check for duplicates, and store it.

    The duplicate check is performed by the UNIQUE constraint on the email
    column. If a lead with the same email already exists, a 409 Conflict
    response is returned with the existing lead's ID.
    """
    async with get_db_connection() as db:
        try:
            cursor = await db.execute(
                """
                INSERT INTO leads (name, email, phone, company, message, status)
                VALUES (?, ?, ?, ?, ?, 'new')
                """,
                (lead.name, lead.email, lead.phone, lead.company, lead.message),
            )
            await db.commit()
            lead_id = cursor.lastrowid

        except sqlite3.IntegrityError:
            # UNIQUE constraint violated -- this email already exists.
            cursor = await db.execute(
                "SELECT id FROM leads WHERE email = ?", (lead.email,)
            )
            existing = await cursor.fetchone()
            existing_id = existing["id"] if existing else "unknown"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A lead with email '{lead.email}' already exists "
                    f"(lead_id: {existing_id})"
                ),
            )

        # Fetch the newly created row to return complete data with timestamps.
        cursor = await db.execute(
            "SELECT * FROM leads WHERE id = ?", (lead_id,)
        )
        row = await cursor.fetchone()
        return dict(row)


@router.get(
    "",
    response_model=list[LeadResponse],
    summary="List all leads",
)
async def list_leads():
    """Return all leads ordered by creation date (newest first)."""
    async with get_db_connection() as db:
        cursor = await db.execute(
            "SELECT * FROM leads ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Get a single lead by ID",
    responses={404: {"description": "Lead not found"}},
)
async def get_lead(lead_id: int):
    """Return a single lead by its database ID."""
    async with get_db_connection() as db:
        cursor = await db.execute(
            "SELECT * FROM leads WHERE id = ?", (lead_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead with id {lead_id} not found",
            )
        return dict(row)


@router.post(
    "/{lead_id}/analyze",
    response_model=LeadAnalysisResponse,
    summary="Analyze a lead using Ollama LLM",
    responses={404: {"description": "Lead not found"}},
)
async def analyze_lead(lead_id: int):
    """
    Trigger AI analysis on a lead's message.

    Phase 2: Creates a placeholder analysis record with status 'pending'.
    Phase 3: This will call the Ollama service for actual classification.
    """
    async with get_db_connection() as db:
        # Verify the lead exists.
        cursor = await db.execute(
            "SELECT * FROM leads WHERE id = ?", (lead_id,)
        )
        lead_row = await cursor.fetchone()
        if not lead_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead with id {lead_id} not found",
            )

        # Check if analysis already exists for this lead.
        cursor = await db.execute(
            "SELECT * FROM lead_analysis WHERE lead_id = ?", (lead_id,)
        )
        existing_analysis = await cursor.fetchone()
        if existing_analysis:
            return {
                "lead_id": lead_id,
                "temperature": existing_analysis["temperature"],
                "requirements": json.loads(
                    existing_analysis["requirements"] or "[]"
                ),
                "ai_response": existing_analysis["ai_response"],
                "analysis_status": existing_analysis["analysis_status"],
            }

        # Phase 3: Perform actual Ollama classification.
        # Call the Ollama service to classify the lead message.
        from app.services.ollama_service import classify_lead
        classification = await classify_lead(lead_id, lead_row["message"])
        # Store the results.
        await db.execute(
            """
            INSERT INTO lead_analysis
                (lead_id, temperature, requirements, ai_response, analysis_status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                lead_id,
                classification["temperature"],
                json.dumps(classification["requirements"]),
                classification["ai_response"],
                classification["analysis_status"],
            ),
        )
        # Update lead status based on analysis outcome.
        new_status = "analyzed" if classification["analysis_status"] == "completed" else "analysis_failed"
        await db.execute(
            "UPDATE leads SET status = ? WHERE id = ?",
            (new_status, lead_id),
        )
        await db.commit()

        return {
            "lead_id": lead_id,
            "temperature": classification["temperature"],
            "requirements": classification["requirements"],
            "ai_response": classification["ai_response"],
            "analysis_status": classification["analysis_status"],
        }


@router.patch(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Update lead status",
    responses={404: {"description": "Lead not found"}},
)
async def update_lead_status(lead_id: int, status_update: dict):
    """
    Update the status and/or other fields of an existing lead.

    Accepts a JSON body with optional fields: status, name, phone, company.
    At minimum, 'status' should be provided.
    """
    async with get_db_connection() as db:
        # Verify the lead exists.
        cursor = await db.execute(
            "SELECT * FROM leads WHERE id = ?", (lead_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead with id {lead_id} not found",
            )

        # Build dynamic UPDATE query from provided fields.
        allowed_fields = {"status", "name", "phone", "company"}
        updates = {}
        for field in allowed_fields:
            if field in status_update and status_update[field] is not None:
                updates[field] = status_update[field]

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No valid fields provided for update",
            )

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [lead_id]
        await db.execute(
            f"UPDATE leads SET {set_clause}, updated_at = CURRENT_TIMESTAMP "
            f"WHERE id = ?",
            values,
        )
        await db.commit()

        # Return the updated record.
        cursor = await db.execute(
            "SELECT * FROM leads WHERE id = ?", (lead_id,)
        )
        updated_row = await cursor.fetchone()
        return dict(updated_row)
