"""
app/models.py
Pydantic schemas for request validation and response serialization.

HOW IT WORKS:
- LeadCreate: The incoming payload schema for POST /api/leads.
  Every field uses field_validator decorators to sanitize and validate
  values BEFORE they reach the database layer.
- LeadResponse: The outgoing schema returned to the client after a lead
  is created or retrieved. Includes the database-generated id and timestamps.
- LeadAnalysisResponse: The schema for Ollama classification results.
- AgentQueryRequest / AgentQueryResponse: Schemas for the Hermes agent endpoint.
- ErrorResponse: Standardized error format used across all error handlers.

INTERVIEW NOTES:
- Pydantic v2 uses model_validator and field_validator (not the old @validator).
- By defining strict schemas, we guarantee that the API never accepts malformed
  data. This is the first layer of defense; the database UNIQUE constraint on
  email is the second layer.
- The ConfigDict with from_attributes=True allows constructing response models
  directly from sqlite3.Row objects (which behave like named tuples).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.utils.validators import sanitize_string, validate_email, validate_phone


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class LeadCreate(BaseModel):
    """
    Schema for creating a new lead via POST /api/leads.
    All five fields are mandatory as specified in the assessment.
    """
    name: str
    email: str
    phone: str
    company: str
    message: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        v = sanitize_string(v)
        if not v:
            raise ValueError("name must not be empty")
        return v

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not validate_email(v):
            raise ValueError("invalid email format")
        return v

    @field_validator("phone")
    @classmethod
    def phone_must_be_valid(cls, v: str) -> str:
        v = v.strip()
        if not validate_phone(v):
            raise ValueError(
                "invalid phone format: must contain 7-15 digits"
            )
        return v

    @field_validator("company")
    @classmethod
    def company_must_not_be_empty(cls, v: str) -> str:
        v = sanitize_string(v)
        if not v:
            raise ValueError("company must not be empty")
        return v

    @field_validator("message")
    @classmethod
    def message_must_not_be_empty(cls, v: str) -> str:
        v = sanitize_string(v)
        if not v:
            raise ValueError("message must not be empty")
        return v


class AgentQueryRequest(BaseModel):
    """Schema for POST /api/agent/query -- natural language instruction."""
    query: str

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        v = sanitize_string(v)
        if not v:
            raise ValueError("query must not be empty")
        return v


# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------

class LeadResponse(BaseModel):
    """Schema returned when a lead is created or retrieved."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str
    company: str
    message: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class LeadAnalysisResponse(BaseModel):
    """Schema for the Ollama classification result."""
    lead_id: int
    temperature: str  # "hot", "warm", or "cold"
    requirements: list[str]
    ai_response: str
    analysis_status: str


class AgentQueryResponse(BaseModel):
    """Schema returned by the Hermes agent endpoint."""
    query: str
    tool_called: Optional[str] = None
    tool_input: Optional[dict] = None
    result: Optional[dict | list | str] = None
    success: bool
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standardized error response format."""
    detail: str
    status_code: int
